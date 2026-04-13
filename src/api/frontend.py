import os
import logging
import json
import uuid
import shutil
import base64
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import APIRouter, Request, HTTPException, Query, Depends, File, UploadFile, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import stripe

from src.db_service import get_db, User, Business, Transaction, SessionLocal
from src.ai_processor import AIProcessor
from src.google_service import GoogleService
from src.utils import (
    get_state_code, get_uqc_code, upload_whatsapp_media, 
    extract_text_from_pdf, convert_pdf_to_image, get_current_user
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Lazy load AI Processor
ai_processor = AIProcessor()

class SettingsUpdate(BaseModel):
    business_name: str
    business_gstin: str

class OnboardingSetup(BaseModel):
    business_name: str
    business_gstin: Optional[str] = ""

class TransactionSave(BaseModel):
    extraction: Dict
    media_url: Optional[str] = None

@router.get("/user/stats")
async def get_user_stats(whatsapp_id: str = Depends(get_current_user), start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
    """Fetches real-time stats for the dashboard with optional date filtering"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        raise HTTPException(status_code=401, detail="Unauthorized: User not linked to Google")
    
    # Get active business
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
        # Fallback to first business if any
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        raise HTTPException(status_code=401, detail="Unauthorized: No business profile found")

    # 1. Fetch Google Sheets totals
    gs = GoogleService(user.google_refresh_token)
    ledger_stats = await gs.get_ledger_stats(business.master_ledger_sheet_id, start_date, end_date)
    
    # 2. Return aggregated stats
    return {
        "bills": ledger_stats["count"],
        "sales": ledger_stats["total_sales"],
        "purchases": ledger_stats["total_purchases"],
        "payments": ledger_stats["total_payments"],
        "expenses": ledger_stats["total_expenses"],
        "expenses_paid": ledger_stats["paid_expenses"],
        "expenses_unpaid": ledger_stats["unpaid_expenses"],
        "whatsapp_id": user.whatsapp_id,
        "google_email": user.google_email,
        "drive_folder_id": business.drive_folder_id,
        "sheet_id": business.master_ledger_sheet_id,
        "business_id": business.id,
        "business_name": business.business_name,
        "business_gstin": business.business_gstin
    }

@router.post("/user/onboard")
async def onboard_user(setup: OnboardingSetup, whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Initializes business profile and Google Drive during onboarding"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.google_refresh_token:
        raise HTTPException(status_code=401, detail="User not linked to Google")

    # Check if business already exists
    business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    # Initialize Google Drive with the provided business name
    gs = GoogleService(user.google_refresh_token)
    try:
        # Pass the business name to initialize_user_drive if it supports it
        # Otherwise, it will use the default from env/code
        folder_id, sheet_id, template_id = await gs.initialize_user_drive(business_name=setup.business_name)
        
        if business:
            # Update existing placeholder business
            business.business_name = setup.business_name
            business.business_gstin = setup.business_gstin
            business.drive_folder_id = folder_id
            business.master_ledger_sheet_id = sheet_id
            business.invoice_template_id = template_id
        else:
            # Create new business if none exists
            business_id = str(uuid.uuid4())
            business = Business(
                id=business_id,
                user_whatsapp_id=whatsapp_id,
                business_name=setup.business_name,
                business_gstin=setup.business_gstin,
                drive_folder_id=folder_id,
                master_ledger_sheet_id=sheet_id,
                invoice_template_id=template_id
            )
            db.add(business)
            user.active_business_id = business_id
        
        user.drive_initialized = True
        db.commit()
        return {"status": "success", "message": "Onboarding completed successfully"}
    except Exception as e:
        logger.error(f"Onboarding error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initialize Google Drive: {str(e)}")

@router.post("/user/settings")
async def update_settings(settings: SettingsUpdate, whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Updates user business profile settings"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
         business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        raise HTTPException(status_code=401, detail="Business not found")

    business.business_name = settings.business_name
    business.business_gstin = settings.business_gstin
    db.commit()
    return {"status": "success", "message": "Settings updated successfully"}

@router.post("/billing/create-checkout-session")
async def create_checkout_session(whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Creates a Stripe Checkout Session for subscription"""
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': os.getenv("STRIPE_PRICE_ID_PRO", "price_default_mock"),
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f"{os.getenv('FRONTEND_URL')}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/dashboard",
            client_reference_id=whatsapp_id,
            customer_email=user.google_email
        )
        return {"url": checkout_session.url}
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handles Stripe Webhooks to update subscription status"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid payload/signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        whatsapp_id = session.get("client_reference_id")
        if whatsapp_id:
            user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
            if user:
                user.subscription_status = "PRO"
                db.commit()
                logger.info(f"User {whatsapp_id} upgraded to PRO")

    return {"status": "success"}

@router.get("/user/businesses")
async def list_businesses(whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists all businesses linked to a WhatsApp ID"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    businesses = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).all()
    return {
        "active_business_id": user.active_business_id,
        "businesses": [
            {
                "id": b.id,
                "name": b.business_name,
                "gstin": b.business_gstin,
                "is_active": b.is_active
            } for b in businesses
        ]
    }

@router.post("/user/businesses/switch")
async def switch_business(business_id: str, whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Switches the active business for a user"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    business = db.query(Business).filter(Business.id == business_id, Business.user_whatsapp_id == whatsapp_id).first()
    if not business:
        raise HTTPException(status_code=401, detail="Business not found or doesn't belong to user")
    
    user.active_business_id = business_id
    db.commit()
    return {"status": "success", "message": f"Switched to {business.business_name}"}

@router.post("/user/businesses/add")
async def add_business(business_name: str, business_gstin: str, whatsapp_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Adds a new business for a user (Sub-merchant onboarding)"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        raise HTTPException(status_code=401, detail="User not linked to Google")
    
    # Initialize Google Drive for new business
    gs = GoogleService(user.google_refresh_token)
    folder_id, sheet_id, template_id = await gs.initialize_user_drive(business_name=business_name)
    
    business_id = str(uuid.uuid4())
    new_business = Business(
        id=business_id,
        user_whatsapp_id=whatsapp_id,
        business_name=business_name,
        business_gstin=business_gstin,
        drive_folder_id=folder_id,
        master_ledger_sheet_id=sheet_id,
        invoice_template_id=template_id
    )
    db.add(new_business)
    # Automatically switch to the new business
    user.active_business_id = business_id
    db.commit()
    
    return {"status": "success", "business_id": business_id}

@router.post("/transactions/process-image")
async def process_image_fe(
    file: UploadFile = File(...), 
    whatsapp_id: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Processes an uploaded bill image or PDF for the frontend"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Save temporary file
    temp_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    temp_path = os.path.join("temp_media", f"fe_{temp_id}{ext}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        extraction = None
        # Process with AI
        if ext in [".jpg", ".jpeg", ".png"]:
            with open(temp_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                image_data_uri = f"data:image/jpeg;base64,{encoded_image}"
                extraction = ai_processor.process_purchase_image(image_data_uri)
        elif ext == ".pdf":
            # Convert PDF to Image for Vision analysis
            image_path = convert_pdf_to_image(temp_path)
            if image_path:
                with open(image_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                    image_data_uri = f"data:image/jpeg;base64,{encoded_image}"
                    extraction = ai_processor.process_purchase_image(image_data_uri)
                # Cleanup temp image
                if os.path.exists(image_path): os.remove(image_path)
            else:
                # Fallback to text extraction
                pdf_text = extract_text_from_pdf(temp_path)
                if pdf_text:
                    extraction = ai_processor.process_sales_text(f"Extract GST data from this bill PDF content: {pdf_text}")
        
        if not extraction:
            raise HTTPException(status_code=500, detail="AI extraction failed")
        
        # Save pending transaction to DB for reference
        pending_tx = Transaction(
            id=temp_id,
            user_whatsapp_id=whatsapp_id,
            business_id=user.active_business_id,
            transaction_type="PENDING",
            media_url=temp_path,
            extracted_json=extraction,
            status="FE_PENDING_CONFIRM"
        )
        db.add(pending_tx)
        db.commit()
        
        return {"transaction_id": temp_id, "extraction": extraction}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions/process-text")
async def process_text_fe(
    text: str = Query(...), 
    whatsapp_id: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Processes a text entry for the frontend"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    extraction = ai_processor.process_sales_text(text)
    if not extraction:
        raise HTTPException(status_code=500, detail="AI extraction failed")
    
    return {"extraction": extraction}

@router.post("/transactions/process-voice")
async def process_voice_fe(
    file: UploadFile = File(...), 
    whatsapp_id: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Transcribes audio and processes it for the frontend"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Save temporary audio file
    temp_id = str(uuid.uuid4())
    # Try to keep extension from file, or default to .webm (common from browsers)
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_path = f"temp_voice_{temp_id}{ext}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. Transcribe with Whisper
        transcript = ai_processor.transcribe_audio(temp_path)
        if not transcript:
            raise HTTPException(status_code=500, detail="Transcription failed")
            
        # 2. Process transcript text
        extraction = ai_processor.process_sales_text(transcript)
        if not extraction:
            raise HTTPException(status_code=500, detail="AI extraction failed")
            
        return {"transcript": transcript, "extraction": extraction}
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/transactions/save")
async def save_transaction_fe(
    data: TransactionSave = Body(...), 
    whatsapp_id: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Finalizes and saves a transaction to Google Sheets/Drive from FE"""
    try:
        logger.info(f"Saving transaction for user: {whatsapp_id}")
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        business = db.query(Business).filter(Business.id == user.active_business_id).first()
        if not business:
            raise HTTPException(status_code=401, detail="Business not found")
        
        extraction = data.extraction
        logger.info(f"Extraction to save: {extraction}")
        final_type = extraction.get("transaction_type", "Sale")
        
        # Robust data parsing from both AI and Manual frontend inputs
        # 1. Basic Fields Mapping
        party_name = extraction.get("party_name") or extraction.get("vendor_name") or extraction.get("customer_name") or "B2C Customer"
        party_gstin = (extraction.get("party_gstin") or extraction.get("recipient_gstin") or "").strip().upper()
        invoice_no = extraction.get("invoice_no") or extraction.get("reference_id") or ""
        date = extraction.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # 2. Amount and GST Rates Parsing
        try:
            total_amount = float(str(extraction.get("total_amount", 0)).replace(",", ""))
        except:
            total_amount = 0.0
            
        try:
            gst_rate = float(str(extraction.get("gst_rate", 0)).replace("%", ""))
        except:
            gst_rate = 0.0
            
        # 3. Tax Calculation (if not provided by extraction)
        taxable_value = extraction.get("taxable_value")
        cgst = extraction.get("cgst")
        sgst = extraction.get("sgst")
        igst = extraction.get("igst")
        
        place_of_supply = extraction.get("place_of_supply", business.business_gstin[:2] if business.business_gstin else "37")
        is_inter_state = False
        if business.business_gstin and len(business.business_gstin) >= 2 and party_gstin and len(party_gstin) >= 2:
            is_inter_state = business.business_gstin[:2] != party_gstin[:2]

        if taxable_value is None or taxable_value == 0:
            if gst_rate > 0:
                taxable_value = total_amount / (1 + (gst_rate / 100))
                total_tax = total_amount - taxable_value
                if is_inter_state:
                    igst = total_tax
                    cgst = 0
                    sgst = 0
                else:
                    cgst = total_tax / 2
                    sgst = total_tax / 2
                    igst = 0
            else:
                taxable_value = total_amount
                cgst = sgst = igst = 0

        # Round values for display
        taxable_value = round(float(taxable_value or 0), 2)
        cgst = round(float(cgst or 0), 2)
        sgst = round(float(sgst or 0), 2)
        igst = round(float(igst or 0), 2)
        
        # 4. Handle "Payment" type separately (Different Google Sheet Schema)
        if final_type == "Payment":
            payment_row = [
                party_name,
                total_amount,
                "One-time", # Default
                "-",
                date,
                "-",
                extraction.get("payment_mode", "Online"),
                extraction.get("notes", "")
            ]
            gs = GoogleService(user.google_refresh_token)
            await gs.append_to_master_ledger(business.master_ledger_sheet_id, payment_row, sheet_name="Payments")
        else:
            # 5. Ledger Row Preparation (Sale, Purchase, Expense)
            # Support multiple items from frontend
            items = extraction.get("items") or [{
                "hsn_code": extraction.get("hsn_code", ""),
                "hsn_description": extraction.get("hsn_description", ""),
                "uqc": extraction.get("uqc", "OTH"),
                "quantity": extraction.get("quantity", 1),
                "gst_rate": gst_rate,
                "taxable_value": taxable_value,
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "total_amount": total_amount
            }]

            gs = GoogleService(user.google_refresh_token)
            for item in items:
                # Schema from GoogleService._get_ledger_headers (21 columns)
                row = [
                    party_gstin,             # 0: Recipient GSTIN
                    party_name,              # 1: Receiver Name
                    invoice_no,              # 2: Invoice Number
                    date,                    # 3: Invoice date
                    item.get("total_amount", 0), # 4: Invoice Value (Row Value)
                    get_state_code(place_of_supply), # 5: Place Of Supply
                    extraction.get("reverse_charge", "N"), # 6: Reverse Charge
                    "B2B" if party_gstin else "B2CS", # 7: Invoice Type
                    final_type,              # 8: Transaction Type
                    item.get("hsn_code", ""), # 9: HSN Code
                    item.get("hsn_description", ""), # 10: HSN Description
                    get_uqc_code(item.get("uqc", "OTH")), # 11: UQC
                    item.get("quantity", 1), # 12: Quantity
                    item.get("gst_rate", 0), # 13: Rate
                    item.get("taxable_value", 0), # 14: Taxable Value
                    item.get("cgst", 0), # 15: CGST
                    item.get("sgst", 0), # 16: SGST
                    item.get("igst", 0), # 17: IGST
                    0,                       # 18: Cess Amount
                    extraction.get("payment_mode", "Paid"), # 19: Payment Status
                    extraction.get("due_date", "") # 20: Due Date
                ]
                await gs.append_to_master_ledger(business.master_ledger_sheet_id, row, sheet_name=final_type)
        
        if data.media_url and os.path.exists(data.media_url):
            await gs.upload_bill_image(data.media_url, business.drive_folder_id)
            os.remove(data.media_url)
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/reports")
async def get_user_reports(whatsapp_id: str, start_date: str = None, end_date: str = None):
    """Fetches transaction history with optional date filtering"""
    with SessionLocal() as db:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user or not user.google_refresh_token:
            raise HTTPException(status_code=401, detail="User not found or not linked to Google")
        
        business = db.query(Business).filter(Business.id == user.active_business_id).first()
        if not business:
            business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not business:
            raise HTTPException(status_code=401, detail="Business not found")

        gs = GoogleService(user.google_refresh_token)
        rows = await gs.get_ledger_rows(business.master_ledger_sheet_id, start_date, end_date)
        return {"rows": rows}

@router.get("/user/reports/download")
async def download_gstr1(whatsapp_id: str, start_date: str = None, end_date: str = None):
    """Generates and returns GSTR-1 JSON file"""
    with SessionLocal() as db:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user or not user.google_refresh_token:
            raise HTTPException(status_code=401, detail="User not found or not linked to Google")
        
        business = db.query(Business).filter(Business.id == user.active_business_id).first()
        if not business:
             business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not business:
            raise HTTPException(status_code=401, detail="Business profile not found")

        gs = GoogleService(user.google_refresh_token)
        user_gstin = business.business_gstin or "37ABCDE1234F1Z5" 
        fp = "032026"
        if start_date:
            parts = start_date.split("-")
            if len(parts) == 3:
                fp = f"{parts[1]}{parts[2]}"

        gstr1_data = await gs.generate_gstr1_json(business.master_ledger_sheet_id, user_gstin, fp)
        if not gstr1_data:
            raise HTTPException(status_code=404, detail="No data found for the selected period")

        return gstr1_data

@router.get("/user/invoice/pdf")
async def get_invoice_pdf(whatsapp_id: str, invoice_no: str, db: Session = Depends(get_db)):
    """Generates and serves a PDF invoice for a specific transaction"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        raise HTTPException(status_code=401, detail="User not found")
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
         business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        raise HTTPException(status_code=401, detail="Business not found")
        
    gs = GoogleService(user.google_refresh_token)
    user_profile = {
        "business_name": business.business_name,
        "business_gstin": business.business_gstin or ""
    }
    
    pdf_buffer = await gs.generate_invoice_pdf_buffer(business.master_ledger_sheet_id, invoice_no, user_profile)
    if not pdf_buffer:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=Invoice_{invoice_no}.pdf"
    })

@router.post("/user/generate-link-token")
async def generate_link_token(whatsapp_id: str, db: Session = Depends(get_db)):
    """Generates a fresh link token for an existing web user"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    token = secrets.token_hex(3).upper()
    user.link_token = token
    user.link_token_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.commit()
    
    return {"link_token": token}

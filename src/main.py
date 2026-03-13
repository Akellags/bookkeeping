import os
import logging
import json
from fastapi import FastAPI, Request, HTTPException, Query, Depends, Response, File, UploadFile, Body
from fastapi.exceptions import RequestValidationError
from typing import Optional, Dict, Any
import shutil
import base64
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from src.ai_processor import AIProcessor
from src.transcription_service import TranscriptionService
from src.google_service import GoogleService
from src.scheduler import init_scheduler
from src.utils import get_whatsapp_media_url, download_whatsapp_media, send_whatsapp_text, send_whatsapp_interactive, get_state_code, get_uqc_code
from src.db_service import get_user, save_user_token, SessionLocal, User, Transaction, get_db, Business, get_active_business
import uuid

# Load environment variables
load_dotenv()

# WhatsApp Webhook Verification Token
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "me_as_verify_token")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Help U - Bookkeeper Backend")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Logs validation errors for debugging"""
    logger.error(f"Validation error for {request.method} {request.url}: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return Response(status_code=422, content=json.dumps({"detail": exc.errors()}), media_type="application/json")

# Global AI Processors (initialized on startup)
ai_processor = None
transcription_service = None

@app.on_event("startup")
async def startup_event():
    """Initializes background tasks and AI models on server start"""
    global ai_processor, transcription_service
    init_scheduler()
    ai_processor = AIProcessor()
    # Initialize Whisper only if needed or in a background thread to avoid blocking startup
    # But for simplicity, we'll keep it here but with a log
    logger.info("Initializing Transcription Service (Whisper)...")
    transcription_service = TranscriptionService()
    logger.info("Application startup complete.")

# API Routes go here...
@app.post("/api/auth/logout")
async def logout():
    """Clears user session/tokens"""
    # In a real app with cookies/JWT, we would clear them here
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/user/stats")
async def get_user_stats(whatsapp_id: str, start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
    """Fetches real-time stats for the dashboard with optional date filtering"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        return {"bills": 0, "sales": 0, "purchases": 0}
    
    # Get active business
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
        # Fallback to first business if any
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        return {"bills": 0, "sales": 0, "purchases": 0, "google_email": user.google_email}

    # 1. Fetch Google Sheets totals
    gs = GoogleService(user.google_refresh_token)
    ledger_stats = gs.get_ledger_stats(business.master_ledger_sheet_id, start_date, end_date)
    
    # 2. Return aggregated stats
    return {
        "bills": ledger_stats["count"],
        "sales": ledger_stats["total_sales"],
        "purchases": ledger_stats["total_purchases"],
        "whatsapp_id": user.whatsapp_id,
        "google_email": user.google_email,
        "drive_folder_id": business.drive_folder_id,
        "sheet_id": business.master_ledger_sheet_id,
        "business_id": business.id,
        "business_name": business.business_name or "Help U Traders",
        "business_gstin": business.business_gstin or "37ABCDE1234F1Z5"
    }

class SettingsUpdate(BaseModel):
    business_name: str
    business_gstin: str

@app.post("/api/user/settings")
async def update_settings(whatsapp_id: str, settings: SettingsUpdate, db: Session = Depends(get_db)):
    """Updates user business profile settings"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
         business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.business_name = settings.business_name
    business.business_gstin = settings.business_gstin
    db.commit()
    return {"status": "success", "message": "Settings updated successfully"}

# Google OAuth2 Configuration
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")]
    }
}
SCOPES = ["https://www.googleapis.com/auth/drive.file", "openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/documents"]

import stripe

# ... (other imports)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.post("/api/billing/create-checkout-session")
async def create_checkout_session(whatsapp_id: str, db: Session = Depends(get_db)):
    """Creates a Stripe Checkout Session for subscription"""
    try:
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # In a real app, use environment variables for Price IDs
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

@app.post("/api/billing/webhook")
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

@app.get("/api/user/businesses")
async def list_businesses(whatsapp_id: str, db: Session = Depends(get_db)):
    """Lists all businesses linked to a WhatsApp ID"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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

@app.post("/api/user/businesses/switch")
async def switch_business(whatsapp_id: str, business_id: str, db: Session = Depends(get_db)):
    """Switches the active business for a user"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    business = db.query(Business).filter(Business.id == business_id, Business.user_whatsapp_id == whatsapp_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found or doesn't belong to user")
    
    user.active_business_id = business_id
    db.commit()
    return {"status": "success", "message": f"Switched to {business.business_name}"}

@app.post("/api/user/businesses/add")
async def add_business(whatsapp_id: str, business_name: str, business_gstin: str, db: Session = Depends(get_db)):
    """Adds a new business for a user (Sub-merchant onboarding)"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        raise HTTPException(status_code=404, detail="User not linked to Google")
    
    # Initialize Google Drive for new business
    gs = GoogleService(user.google_refresh_token)
    folder_id, sheet_id, template_id = gs.initialize_user_drive()
    
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

@app.post("/api/transactions/process-image")
async def process_image_fe(
    whatsapp_id: str = Query(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """Processes an uploaded bill image for the frontend"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Save temporary file
    temp_id = str(uuid.uuid4())
    temp_path = f"temp_{temp_id}.jpg"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process with AI
        with open(temp_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            image_data_uri = f"data:image/jpeg;base64,{encoded_image}"
            extraction = ai_processor.process_purchase_image(image_data_uri)
        
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
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions/process-text")
async def process_text_fe(
    whatsapp_id: str = Query(...), 
    text: str = Query(...), 
    db: Session = Depends(get_db)
):
    """Processes a text entry for the frontend"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    extraction = ai_processor.process_sales_text(text)
    if not extraction:
        raise HTTPException(status_code=500, detail="AI extraction failed")
    
    return {"extraction": extraction}

class TransactionSave(BaseModel):
    extraction: Dict
    media_url: Optional[str] = None

@app.post("/api/transactions/save")
async def save_transaction_fe(
    whatsapp_id: str = Query(...), 
    data: TransactionSave = Body(...), 
    db: Session = Depends(get_db)
):
    """Finalizes and saves a transaction to Google Sheets/Drive from FE"""
    try:
        logger.info(f"Saving transaction for user: {whatsapp_id}")
        user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        business = db.query(Business).filter(Business.id == user.active_business_id).first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        extraction = data.extraction
        logger.info(f"Extraction to save: {extraction}")
        final_type = extraction.get("transaction_type", "Sale")
    
        row = [
            extraction.get("recipient_gstin", ""), 
            extraction.get("vendor_name" if final_type == "Purchase" else "customer_name", "B2C Customer"),
            extraction.get("invoice_no", ""),
            extraction.get("date", ""),
            extraction.get("total_amount", 0),
            get_state_code(extraction.get("place_of_supply", "37")),
            extraction.get("reverse_charge", "N"),
            "B2B" if extraction.get("recipient_gstin") else "B2CS",
            final_type,
            extraction.get("hsn_code", ""),
            extraction.get("hsn_description", ""),
            get_uqc_code(extraction.get("uqc", "OTH")),
            extraction.get("quantity", 1),
            extraction.get("gst_rate", 0),
            extraction.get("taxable_value", 0),
            extraction.get("cgst", 0),
            extraction.get("sgst", 0),
            extraction.get("igst", 0),
            0 # Cess
        ]
        
        gs = GoogleService(user.google_refresh_token)
        gs.append_to_master_ledger(business.master_ledger_sheet_id, row)
        
        if data.media_url and os.path.exists(data.media_url):
            gs.upload_bill_image(data.media_url, business.drive_folder_id)
            os.remove(data.media_url)
            
        # Generate PDF Invoice if Sale
        if final_type == "Sale" and business.invoice_template_id:
            try:
                logger.info(f"Attempting to generate PDF invoice for template {business.invoice_template_id}...")
                invoice_data = {
                    "business_name": business.business_name or "Help U Traders",
                    "business_gstin": business.business_gstin or "37ABCDE1234F1Z5",
                    "invoice_no": extraction.get("invoice_no", ""),
                    "date": extraction.get("date", ""),
                    "customer_name": extraction.get("customer_name", "B2C Customer"),
                    "recipient_gstin": extraction.get("recipient_gstin", ""),
                    "hsn_code": extraction.get("hsn_code", ""),
                    "gst_rate": extraction.get("gst_rate", 0),
                    "taxable_value": extraction.get("taxable_value", 0),
                    "cgst": extraction.get("cgst", 0),
                    "sgst": extraction.get("sgst", 0),
                    "igst": extraction.get("igst", 0),
                    "total_amount": extraction.get("total_amount", 0)
                }
                gs.generate_sales_invoice(business.invoice_template_id, invoice_data, business.drive_folder_id)
                logger.info("Successfully generated PDF invoice.")
            except Exception as inv_err:
                logger.warning(f"Failed to generate PDF invoice: {inv_err}. Transaction was still saved to ledger.")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/reports")
async def get_user_reports(whatsapp_id: str, start_date: str = None, end_date: str = None):
    """Fetches transaction history with optional date filtering"""
    db = SessionLocal()
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        db.close()
        return {"rows": []}
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
        business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        db.close()
        return {"rows": []}

    gs = GoogleService(user.google_refresh_token)
    rows = gs.get_ledger_rows(business.master_ledger_sheet_id, start_date, end_date)
    db.close()
    return {"rows": rows}

@app.get("/api/user/reports/download")
async def download_gstr1(whatsapp_id: str, start_date: str = None, end_date: str = None):
    """Generates and returns GSTR-1 JSON file"""
    db = SessionLocal()
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
         business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        db.close()
        raise HTTPException(status_code=404, detail="Business profile not found")

    gs = GoogleService(user.google_refresh_token)
    user_gstin = business.business_gstin or "37ABCDE1234F1Z5" 
    # Use the first start_date month or current month for fp
    fp = "032026"
    if start_date:
        parts = start_date.split("-")
        if len(parts) == 3:
            fp = f"{parts[1]}{parts[2]}"

    gstr1_data = gs.generate_gstr1_json(business.master_ledger_sheet_id, user_gstin, fp)
    db.close()

    if not gstr1_data:
        raise HTTPException(status_code=404, detail="No data found for the selected period")

    return gstr1_data

@app.get("/api/user/invoice/pdf")
async def get_invoice_pdf(whatsapp_id: str, invoice_no: str, db: Session = Depends(get_db)):
    """Generates and serves a PDF invoice for a specific transaction"""
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user or not user.google_refresh_token:
        raise HTTPException(status_code=404, detail="User not found")
    
    business = db.query(Business).filter(Business.id == user.active_business_id).first()
    if not business:
         business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    gs = GoogleService(user.google_refresh_token)
    user_profile = {
        "business_name": business.business_name or "Help U Traders",
        "business_gstin": business.business_gstin or "37ABCDE1234F1Z5"
    }
    
    pdf_buffer = gs.generate_invoice_pdf_buffer(business.master_ledger_sheet_id, invoice_no, user_profile)
    if not pdf_buffer:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=Invoice_{invoice_no}.pdf"
    })

@app.get("/auth/google")
async def google_login(whatsapp_id: str = Query(...)):
    """Initializes Google OAuth2 flow with whatsapp_id in state"""
    if not GOOGLE_CLIENT_CONFIG["web"]["client_id"]:
        return {"error": "Google Client ID not configured"}
    
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=GOOGLE_CLIENT_CONFIG["web"]["redirect_uris"][0]
    )
    # Pass whatsapp_id in state to link accounts on callback
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', state=whatsapp_id)
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def google_callback(code: str, state: str = None):
    """Handles Google OAuth2 callback and links to WhatsApp ID"""
    try:
        whatsapp_id = state
        if not whatsapp_id:
             return RedirectResponse(url="/auth-error?message=Missing identification state")

        # For non-WhatsApp signups, generate a unique ID
        is_new_user = False
        if whatsapp_id == "new_user":
             whatsapp_id = f"web_{uuid.uuid4().hex[:12]}"
             is_new_user = True

        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=GOOGLE_CLIENT_CONFIG["web"]["redirect_uris"][0]
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get actual user info (Email/Name)
        session = flow.authorized_session()
        user_info = session.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        email = user_info.get("email", "user@example.com")
        
        # Save user to DB (handles merging if email already exists)
        user = save_user_token(whatsapp_id, email, credentials.refresh_token)
        whatsapp_id = user.whatsapp_id # Use the ID from DB
        
        # Check if user already has an active business profile
        db = SessionLocal()
        db_user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        existing_business = db.query(Business).filter(Business.user_whatsapp_id == whatsapp_id).first()
        
        if not existing_business:
            # Only then initialize Google Drive Folder/Sheet/Template
            gs = GoogleService(credentials.refresh_token)
            folder_id, sheet_id, template_id = gs.initialize_user_drive()
            
            # Update user with first business
            business_id = str(uuid.uuid4())
            new_business = Business(
                id=business_id,
                user_whatsapp_id=whatsapp_id,
                business_name="Help U Traders", # Default
                business_gstin="37ABCDE1234F1Z5", # Default
                drive_folder_id=folder_id,
                master_ledger_sheet_id=sheet_id,
                invoice_template_id=template_id
            )
            db.add(new_business)
            if db_user:
                db_user.active_business_id = business_id
            db.commit()
        db.close()

        logger.info(f"Successfully linked Google account for {whatsapp_id}")
        
        # Redirect to React Success Page with the ID so frontend can save it
        return RedirectResponse(url=f"/onboarding-success?whatsapp_id={whatsapp_id}")
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        # Return a friendly error redirect instead of JSON
        error_msg = str(e)
        if "active_business_id" in error_msg:
             error_msg = "Database schema mismatch. Please contact support."
        elif "Google Docs API" in error_msg:
             error_msg = "Google Docs API is disabled in your project. Please enable it in Google Cloud Console and try again."
        elif "invalid_grant" in error_msg:
             error_msg = "Google authentication expired. Please try again."
        return RedirectResponse(url=f"/auth-error?message={error_msg}")

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """WhatsApp Webhook Verification"""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    else:
        logger.error("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_whatsapp_message(request: Request):
    """Handles incoming WhatsApp messages and media"""
    payload = await request.json()
    logger.info(f"Received WhatsApp payload: {payload}")
    
    try:
        # Extract messages from the payload
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages_list = value.get("messages", [])
        
        if not messages_list:
            return {"status": "no messages"}

        messages = messages_list[0]
        user_whatsapp_id = messages.get("from")
        message_type = messages.get("type")
        
        # 1. Check if user is linked
        user = get_user(user_whatsapp_id)
        if not user or not user.google_refresh_token:
            # Generate onboarding URL
            # Use the base URL from the redirect URI (remove the path)
            redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
            base_url = redirect_uri.split('/auth/callback')[0]
            onboarding_url = f"{base_url}/auth/google?whatsapp_id={user_whatsapp_id}"
            send_whatsapp_text(user_whatsapp_id, f"Welcome to Help U! 🚀\nPlease link your Google Drive to start bookkeeping: {onboarding_url}")
            return {"status": "onboarding_sent"}
        
        # Get active business
        business = get_active_business(user_whatsapp_id)
        if not business:
            send_whatsapp_text(user_whatsapp_id, "Please set up your business profile first on the Help U dashboard.")
            return {"status": "business_not_set"}
            
        gs = GoogleService(user.google_refresh_token)
        
        if message_type == "image":
            # 1. Download Media
            image_id = messages.get("image", {}).get("id")
            media_url = get_whatsapp_media_url(image_id)
            if media_url:
                local_path = f"temp_{image_id}.jpg"
                download_whatsapp_media(media_url, local_path)
                
                # 2. Store pending transaction in DB
                db = SessionLocal()
                pending_tx = Transaction(
                    id=str(uuid.uuid4()),
                    user_whatsapp_id=user_whatsapp_id,
                    business_id=business.id,
                    transaction_type="PENDING",
                    media_url=local_path,
                    status="PENDING_TYPE"
                )
                db.add(pending_tx)
                db.commit()
                db.close()

                # 3. Ask user for type via Buttons
                send_whatsapp_interactive(
                    user_whatsapp_id, 
                    f"I've received your image for {business.business_name}! 📸 Is this a Sale Receipt or a Purchase Invoice?",
                    ["Sale Receipt", "Purchase Invoice"]
                )
                return {"status": "awaiting_type"}

        elif message_type == "interactive":
            # Handle button response
            interactive = messages.get("interactive", {})
            if interactive.get("type") == "button_reply":
                button_title = interactive.get("button_reply", {}).get("title")
                
                # Fetch pending transaction
                db = SessionLocal()
                tx = db.query(Transaction).filter(
                    Transaction.user_whatsapp_id == user_whatsapp_id,
                    Transaction.status == "PENDING_TYPE"
                ).order_by(Transaction.created_at.desc()).first()
                
                if tx and os.path.exists(tx.media_url):
                    local_path = tx.media_url
                    # Process with AI
                    with open(local_path, "rb") as image_file:
                        import base64
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                        image_data_uri = f"data:image/jpeg;base64,{encoded_image}"
                        extraction = ai_processor.process_purchase_image(image_data_uri)
                    
                    if extraction:
                        # Override transaction type based on button
                        final_type = "Sale" if "Sale" in button_title else "Purchase"
                        
                        row = [
                            extraction.get("recipient_gstin", ""), 
                            extraction.get("vendor_name" if final_type == "Purchase" else "customer_name", "B2C Customer"),
                            extraction.get("invoice_no", ""),
                            extraction.get("date", ""),
                            extraction.get("total_amount", 0),
                            get_state_code(extraction.get("place_of_supply", "37")),
                            extraction.get("reverse_charge", "N"),
                            "B2B" if extraction.get("recipient_gstin") else "B2CS",
                            final_type,
                            extraction.get("hsn_code", ""),
                            extraction.get("hsn_description", ""),
                            get_uqc_code(extraction.get("uqc", "OTH")),
                            extraction.get("quantity", 1),
                            extraction.get("gst_rate", 0),
                            extraction.get("taxable_value", 0),
                            extraction.get("cgst", 0),
                            extraction.get("sgst", 0),
                            extraction.get("igst", 0),
                            0 # Cess
                        ]
                        gs.append_to_master_ledger(business.master_ledger_sheet_id, row)
                        gs.upload_bill_image(local_path, business.drive_folder_id)
                        
                        # Generate PDF Invoice if Sale
                        if final_type == "Sale" and business.invoice_template_id:
                            try:
                                invoice_data = {
                                    "business_name": business.business_name or "Help U Traders",
                                    "business_gstin": business.business_gstin or "37ABCDE1234F1Z5",
                                    "invoice_no": extraction.get("invoice_no", ""),
                                    "date": extraction.get("date", ""),
                                    "customer_name": extraction.get("customer_name", "B2C Customer"),
                                    "recipient_gstin": extraction.get("recipient_gstin", ""),
                                    "hsn_code": extraction.get("hsn_code", ""),
                                    "gst_rate": extraction.get("gst_rate", 0),
                                    "taxable_value": extraction.get("taxable_value", 0),
                                    "cgst": extraction.get("cgst", 0),
                                    "sgst": extraction.get("sgst", 0),
                                    "igst": extraction.get("igst", 0),
                                    "total_amount": extraction.get("total_amount", 0)
                                }
                                gs.generate_sales_invoice(business.invoice_template_id, invoice_data, business.drive_folder_id)
                            except Exception as inv_err:
                                logger.warning(f"Failed to generate PDF invoice for WhatsApp: {inv_err}")

                        # Update TX status
                        tx.status = "COMPLETED"
                        tx.transaction_type = final_type
                        tx.extracted_json = extraction
                        db.commit()
                        
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            
                        send_whatsapp_text(user_whatsapp_id, f"✅ Successfully recorded as {final_type}!")
                    else:
                        send_whatsapp_text(user_whatsapp_id, "Failed to extract data. Please try again.")
                else:
                    send_whatsapp_text(user_whatsapp_id, "Session expired or no image found. Please resend the image.")
                db.close()
            return {"status": "interactive_handled"}

        elif message_type == "text" or message_type == "audio":
            if message_type == "audio":
                audio_id = messages.get("audio", {}).get("id")
                media_url = get_whatsapp_media_url(audio_id)
                if media_url:
                    local_path = f"temp_{audio_id}.ogg"
                    download_whatsapp_media(media_url, local_path)
                    text, _ = transcription_service.transcribe_audio(local_path)
                    if os.path.exists(local_path):
                        os.remove(local_path)
                else:
                    text = None
            else:
                text = messages.get("text", {}).get("body")

            if not text:
                send_whatsapp_text(user_whatsapp_id, "Sorry, I couldn't understand that audio message.")
                return {"status": "success"}

            # Handle commands like "Send invoice INV-123"
            if text.lower().startswith("send invoice"):
                invoice_no = text.lower().replace("send invoice", "").strip().upper()
                redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
                base_url = redirect_uri.split('/auth/callback')[0]
                pdf_url = f"{base_url}/api/user/invoice/pdf?whatsapp_id={user_whatsapp_id}&invoice_no={invoice_no}"
                send_whatsapp_text(user_whatsapp_id, f"📄 Here is your requested invoice {invoice_no}:\n{pdf_url}")
                return {"status": "invoice_sent"}

            extraction = ai_processor.process_sales_text(text)
            
            if extraction:
                # 3. Save to Google Sheet (16-column GSTR-1 Format)
                row = [
                    extraction.get("recipient_gstin", ""), 
                    extraction.get("customer_name", "B2C Customer"),
                    extraction.get("invoice_no", f"S-{uuid.uuid4().hex[:6].upper()}"),
                    extraction.get("date", ""),
                    extraction.get("total_amount", 0),
                    get_state_code(extraction.get("place_of_supply", "37")),
                    extraction.get("reverse_charge", "N"),
                    "B2B" if extraction.get("recipient_gstin") else "B2CS",
                    extraction.get("transaction_type", "Sale"),
                    extraction.get("hsn_code", ""),
                    extraction.get("hsn_description", ""),
                    get_uqc_code(extraction.get("uqc", "OTH")),
                    extraction.get("quantity", 1),
                    extraction.get("gst_rate", 0),
                    extraction.get("taxable_value", 0),
                    extraction.get("cgst", 0),
                    extraction.get("sgst", 0),
                    extraction.get("igst", 0),
                    0 # Cess
                ]
                gs.append_to_master_ledger(business.master_ledger_sheet_id, row)
                
                response_text = f"✅ Sale Recorded for {business.business_name}!\n- Amount: ₹{extraction.get('total_amount')}\n- GST: {extraction.get('gst_rate')}%"
                send_whatsapp_text(user_whatsapp_id, response_text)
            else:
                send_whatsapp_text(user_whatsapp_id, "Sorry, I couldn't parse that sales record. Try: 'Sold items worth 500 with 18% GST'")

    except Exception as e:
        logger.error(f"Error handling webhook payload: {e}")

    return {"status": "success"}

# Serve Static Files (Frontend)
# Mount assets folder
app.mount("/assets", StaticFiles(directory="src/frontend/dist/assets"), name="assets")

# Catch-all route to serve index.html for React Router
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    logger.info(f"Serving frontend for path: {full_path}")
    # Check if the path exists as a static file first (like vite.svg)
    static_file = os.path.join("src/frontend/dist", full_path)
    if os.path.isfile(static_file):
        return FileResponse(static_file)
    # Default to index.html for SPA routing
    return FileResponse("src/frontend/dist/index.html")

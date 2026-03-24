import os
import logging
import uuid
import base64
from datetime import datetime
from sqlalchemy.orm import Session
from src.db_service import User, Business, Transaction
from src.utils import (
    send_whatsapp_text, send_whatsapp_interactive, upload_whatsapp_media, 
    send_whatsapp_document, convert_image_to_pdf, is_valid_gstin, 
    get_state_code, get_uqc_code, handle_google_error
)
from src.ai_processor import AIProcessor
from src.google_service import GoogleService

logger = logging.getLogger(__name__)

ai_processor = AIProcessor()

async def handle_interactive(db: Session, user: User, business: Business, message_data: dict):
    """Handles interactive responses (buttons and lists)"""
    user_whatsapp_id = user.whatsapp_id
    interactive = message_data.get("interactive", {})
    if interactive.get("type") != "button_reply":
        return {"status": "unsupported_interactive"}

    button_title = interactive.get("button_reply", {}).get("title")
    
    # 1. Handle Business Switch
    target_business = db.query(Business).filter(
        Business.user_whatsapp_id == user_whatsapp_id,
        Business.business_name == button_title
    ).first()
    
    if target_business:
        user.active_business_id = target_business.id
        db.commit()
        send_whatsapp_text(user_whatsapp_id, f"✅ Switched to *{target_business.business_name}*. All new records will be saved here.")
        return {"status": "switched_business"}

    # 2. Handle Payment Status (Paid/Credit)
    if button_title in ["Paid", "Credit"]:
        if user.last_interaction_type == "AWAITING_PAYMENT":
            return await _handle_payment_status(db, user, business, button_title)

    # 3. Handle Top-Level Buckets (Money In, Money Out, Business Tools)
    btn_clean = button_title.lower().strip()
    if any(x in btn_clean for x in ["money in", "money out", "business tools"]):
        tx = db.query(Transaction).filter(
            Transaction.user_whatsapp_id == user_whatsapp_id,
            Transaction.status.in_(["PENDING_TYPE", "PENDING_SUBTYPE", "PENDING_CONFIRM"])
        ).order_by(Transaction.created_at.desc()).first()

        if not tx:
            # Create a fresh placeholder transaction if one doesn't exist (e.g. from "Hi" menu)
            tx = Transaction(
                id=str(uuid.uuid4()),
                user_whatsapp_id=user_whatsapp_id,
                business_id=business.id,
                transaction_type="PENDING",
                status="PENDING_TYPE"
            )
            db.add(tx)
            db.commit()
        
        return await _handle_type_selection(db, user, business, tx, button_title)

    # 4. Handle Existing Transaction Flow
    tx = db.query(Transaction).filter(
        Transaction.user_whatsapp_id == user_whatsapp_id,
        Transaction.status.in_(["PENDING_TYPE", "PENDING_SUBTYPE", "PENDING_CONFIRM"])
    ).order_by(Transaction.created_at.desc()).first()
    
    if not tx:
        send_whatsapp_text(user_whatsapp_id, "Session expired or no pending record found.")
        return {"status": "no_pending_tx"}

    if button_title == "Cancel":
        return await _handle_cancel(db, tx)

    # Step-by-Step Flow
    if tx.status == "PENDING_TYPE":
        return await _handle_type_selection(db, user, business, tx, button_title)
    
    elif tx.status == "PENDING_SUBTYPE":
        return await _handle_subtype_selection(db, user, business, tx, button_title)
    
    elif tx.status == "PENDING_CONFIRM":
        return await _handle_confirmation(db, user, business, tx, button_title)

    return {"status": "unhandled_interactive"}

async def _handle_payment_status(db: Session, user: User, business: Business, status: str):
    data = user.last_interaction_data
    if not data:
        send_whatsapp_text(user.whatsapp_id, "Sorry, I lost track of that transaction. Please try again.")
        return {"status": "error_no_data"}
        
    row_index = data.get("row_index")
    old_row = data.get("old_row")
    
    if not row_index or not old_row:
        send_whatsapp_text(user.whatsapp_id, "Invalid transaction data. Please try again.")
        return {"status": "error_invalid_data"}
    
    gs = GoogleService(user.google_refresh_token)
    new_row = list(old_row)
    
    if status == "Paid":
        new_row[19] = "Paid"
        new_row[20] = "N/A"
        gs.update_ledger_row(business.master_ledger_sheet_id, row_index, new_row)
        send_whatsapp_text(user.whatsapp_id, "✅ Marked as Paid!")
        user.last_interaction_type = None
        user.last_interaction_data = None
    else:
        new_row[19] = "Unpaid"
        gs.update_ledger_row(business.master_ledger_sheet_id, row_index, new_row)
        user.last_interaction_type = "AWAITING_DUEDATE"
        user.last_interaction_data = {"row_index": row_index, "old_row": new_row}
        send_whatsapp_text(user.whatsapp_id, "Please enter the *Due Date* for this payment (e.g., '10th April' or 'In 5 days'):")
    
    db.commit()
    return {"status": "payment_handled"}

async def _handle_cancel(db: Session, tx: Transaction):
    tx.status = "CANCELLED"
    if tx.media_url and os.path.exists(tx.media_url):
        os.remove(tx.media_url)
    db.commit()
    send_whatsapp_text(tx.user_whatsapp_id, "Cancelled. No record was saved.")
    return {"status": "cancelled"}

async def _handle_type_selection(db: Session, user: User, business: Business, tx: Transaction, button_title: str):
    btn_clean = button_title.lower().strip()
    
    if "money in" in btn_clean:
        tx.status = "PENDING_TYPE"
        db.commit()
        send_whatsapp_interactive(
            user.whatsapp_id,
            "Select transaction type for Money In:",
            ["Sale", "Payment Received", "Cancel"]
        )
        return {"status": "awaiting_money_in_type"}

    elif "money out" in btn_clean:
        tx.status = "PENDING_TYPE"
        db.commit()
        send_whatsapp_interactive(
            user.whatsapp_id,
            "Select transaction type for Money Out:",
            ["Purchase", "Expense", "Payment Made", "Cancel"]
        )
        return {"status": "awaiting_money_out_type"}

    elif "business tools" in btn_clean:
        # Business tools are usually list menus or specific commands
        # For now, let's show a list or just text
        send_whatsapp_text(
            user.whatsapp_id,
            "🛠️ *Business Tools*\n\n"
            "📊 *Stats*: Your monthly totals\n"
            "📈 *Analysis*: Deep business report\n"
            "💡 *Advice*: Ask me anything\n"
            "🧾 *GSTR1*: Download JSON report\n"
            "📖 *Ledger*: Access full ledger\n\n"
            "_(Type the command name to use it)_"
        )
        tx.status = "CANCELLED"
        db.commit()
        return {"status": "tools_shown"}

    if button_title in ["Sale", "Purchase"]:
        tx.transaction_type = button_title
        # Check if we have extraction data (fresh start from menu)
        if not tx.extracted_json or "total_amount" not in tx.extracted_json:
            tx.status = "AWAITING_DETAILS"
            db.commit()
            send_whatsapp_text(user.whatsapp_id, f"Great! Please send a photo of the {button_title} bill or type the details (e.g., '{button_title} of 500').")
            return {"status": "awaiting_details"}

        tx.status = "PENDING_SUBTYPE"
        db.commit()
        send_whatsapp_interactive(
            user.whatsapp_id,
            f"Is this a B2B {button_title} (with GSTIN) or B2C (without GSTIN)?",
            ["B2B", "B2C"]
        )
        return {"status": "awaiting_subtype"}
    
    elif button_title == "Expense":
        tx.transaction_type = "Expense"
        # Check if we have extraction data
        if not tx.extracted_json or "total_amount" not in tx.extracted_json:
            tx.status = "AWAITING_DETAILS"
            db.commit()
            send_whatsapp_text(user.whatsapp_id, "Great! Please send a photo of the Expense bill or type the details (e.g., 'Paid 500 for rent').")
            return {"status": "awaiting_details"}

        tx.status = "PENDING_CONFIRM"
        db.commit()
        # Fall through to AI processing/confirmation
        return await _handle_confirmation(db, user, business, tx, "Initial")
    
    elif button_title in ["Payment Received", "Payment Made"]:
        tx.transaction_type = "Payment"
        if not tx.extracted_json: tx.extracted_json = {}
        tx.extracted_json["payment_direction"] = "In" if button_title == "Payment Received" else "Out"
        
        # Check if we have extraction data
        if "total_amount" not in tx.extracted_json:
            tx.status = "AWAITING_DETAILS"
            db.commit()
            send_whatsapp_text(user.whatsapp_id, f"Great! Please send the details for this {button_title} (e.g., 'Received 1000 from Customer').")
            return {"status": "awaiting_details"}

        tx.status = "PENDING_SUBTYPE"
        db.commit()
        send_whatsapp_interactive(
            user.whatsapp_id,
            "Is this a One-time (Single) payment or a Recurring payment?",
            ["Single", "Recurring"]
        )
        return {"status": "awaiting_payment_subtype"}
    
    elif button_title == "Convert to PDF":
        return await _handle_pdf_conversion(db, user, business, tx)

    return {"status": "invalid_type"}

async def _handle_subtype_selection(db: Session, user: User, business: Business, tx: Transaction, button_title: str):
    if button_title in ["B2B", "B2C"]:
        tx.status = "PENDING_CONFIRM"
        if not tx.extracted_json: tx.extracted_json = {}
        tx.extracted_json["is_b2b"] = (button_title == "B2B")
        db.commit()
        return await _handle_confirmation(db, user, business, tx, "Initial")
    
    elif button_title in ["Single", "Recurring"]:
        if not tx.extracted_json: tx.extracted_json = {}
        tx.extracted_json["payment_type"] = button_title
        if button_title == "Recurring":
            send_whatsapp_interactive(
                user.whatsapp_id,
                "What is the frequency of this recurring payment?",
                ["Monthly", "Yearly"]
            )
            db.commit()
            return {"status": "awaiting_frequency"}
        else:
            tx.extracted_json["payment_frequency"] = "N/A"
            tx.status = "PENDING_CONFIRM"
            db.commit()
            return await _handle_confirmation(db, user, business, tx, "Initial")
            
    elif button_title in ["Monthly", "Yearly"]:
        if not tx.extracted_json: tx.extracted_json = {}
        tx.extracted_json["payment_frequency"] = button_title
        tx.status = "PENDING_CONFIRM"
        db.commit()
        return await _handle_confirmation(db, user, business, tx, "Initial")

    return {"status": "invalid_subtype"}

async def _handle_confirmation(db: Session, user: User, business: Business, tx: Transaction, button_title: str):
    extraction = tx.extracted_json
    final_type = tx.transaction_type or "Sale"
    
    # AI Extraction for images
    if tx.media_url and os.path.exists(tx.media_url) and (not extraction or "total_amount" not in extraction):
        with open(tx.media_url, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            image_data_uri = f"data:image/jpeg;base64,{encoded_image}"
            extraction = ai_processor.process_purchase_image(image_data_uri)
            if extraction:
                tx.extracted_json = extraction
                db.commit()

    if not extraction:
        send_whatsapp_text(user.whatsapp_id, "Failed to extract data. Please try again.")
        return {"status": "extraction_failed"}

    if button_title not in ["Confirm", "Cancel"] and tx.status == "PENDING_CONFIRM":
        # Initial request for confirmation
        amount = extraction.get("total_amount", 0)
        is_b2b_selected = extraction.get("is_b2b", False)
        
        display_type = final_type
        if final_type == "Payment":
            p_dir = extraction.get("payment_direction", "N/A")
            display_type = f"Payment {'Received' if p_dir == 'In' else 'Made'}"

        gstin = extraction.get("recipient_gstin") if final_type == "Sale" else extraction.get("vendor_gstin")
        
        if is_b2b_selected and not gstin:
            send_whatsapp_text(user.whatsapp_id, f"I couldn't find a GSTIN in this {display_type}. Please reply with the GSTIN, or say 'N/A' if not applicable.")
            user.last_interaction_type = "AWAITING_GSTIN"
            user.last_interaction_data = {"tx_id": tx.id}
            db.commit()
            return {"status": "awaiting_gstin"}

        warning = ""
        if is_b2b_selected and not is_valid_gstin(gstin) and gstin != "N/A":
            warning = "\n\n⚠️ *Warning:* The GSTIN extracted looks invalid. Please verify."

        send_whatsapp_interactive(
            user.whatsapp_id,
            f"I've parsed a {display_type} for ₹{amount}. Should I record this to your ledger?{warning}",
            ["Confirm", "Cancel"]
        )
        return {"status": "awaiting_confirmation"}

    if button_title == "Confirm":
        return await _finalize_transaction(db, user, business, tx, extraction)

    return {"status": "unhandled_confirm"}

async def _finalize_transaction(db: Session, user: User, business: Business, tx: Transaction, extraction: dict):
    try:
        final_type = tx.transaction_type or "Sale"
        if float(extraction.get("total_amount", 0)) <= 0:
            send_whatsapp_text(user.whatsapp_id, "I couldn't find a valid amount in that message. No record saved.")
            tx.status = "FAILED_VALIDATION"
            if tx.media_url and os.path.exists(tx.media_url): os.remove(tx.media_url)
            db.commit()
            return {"status": "validation_failed"}

        gs = GoogleService(user.google_refresh_token)
        sheet_name = {"Sale": "Sales", "Purchase": "Purchases", "Expense": "Expenses", "Payment": "Payments"}.get(final_type, "Sales")
        
        extracted_date = extraction.get("date")
        if not extracted_date or extracted_date in ["", "null", "N/A"]:
            extracted_date = datetime.now().strftime("%d-%m-%Y")

        last_index = 0
        row = []

        if final_type == "Payment":
            # Payment logic
            p_type = extraction.get("payment_type", "Single")
            p_freq = extraction.get("payment_frequency", "N/A")
            p_dir = extraction.get("payment_direction", "N/A")
            next_due = "N/A"
            if p_type == "Recurring":
                from dateutil.relativedelta import relativedelta
                curr_dt = datetime.strptime(extracted_date, "%d-%m-%Y")
                if p_freq == "Monthly":
                    next_due = (curr_dt + relativedelta(months=1)).strftime("%d-%m-%Y")
                else:
                    next_due = (curr_dt + relativedelta(years=1)).strftime("%d-%m-%Y")

            row = [
                extraction.get("vendor_name" if final_type == "Purchase" else "customer_name", "Vendor/Entity"),
                extraction.get("total_amount", 0), p_type, p_freq, extracted_date, next_due, "Completed",
                f"Direction: {p_dir} | Recorded via WhatsApp {datetime.now().strftime('%Y-%m-%d')}"
            ]
            gs.append_to_master_ledger(business.master_ledger_sheet_id, row, sheet_name="Payments")
        else:
            # Sales/Purchases/Expenses logic
            items = extraction.get("items") or [{
                "hsn_code": extraction.get("hsn_code", ""), "hsn_description": extraction.get("hsn_description", ""),
                "uqc": extraction.get("uqc", "OTH"), "quantity": extraction.get("quantity", 1),
                "gst_rate": extraction.get("gst_rate", 0), "taxable_value": extraction.get("taxable_value", extraction.get("total_amount", 0)),
                "cgst": extraction.get("cgst", 0), "sgst": extraction.get("sgst", 0), "igst": extraction.get("igst", 0),
                "total_amount": extraction.get("total_amount", 0)
            }]

            invoice_no = extraction.get("invoice_no", f"INV-{uuid.uuid4().hex[:6].upper()}")
            business_state_code = (business.business_gstin or "37")[:2]
            pos_state_code = get_state_code(extraction.get("place_of_supply", business_state_code))
            is_intra_state = (business_state_code == pos_state_code)

            for item in items:
                taxable_value = float(item.get("taxable_value", 0))
                gst_rate = float(item.get("gst_rate", 0))
                item_total = float(item.get("total_amount", 0))
                
                # If total_amount is 0 but taxable_value exists, calculate it
                if item_total <= 0 and taxable_value > 0:
                    item_total = taxable_value * (1 + gst_rate/100)

                cgst = sgst = igst = 0
                if is_intra_state:
                    cgst = sgst = round((taxable_value * gst_rate / 200), 2)
                else:
                    igst = round((taxable_value * gst_rate / 100), 2)

                row = [
                    extraction.get("recipient_gstin", ""), extraction.get("vendor_name" if final_type == "Purchase" else "customer_name", "B2C Customer"),
                    invoice_no, extracted_date, round(item_total, 2), pos_state_code, extraction.get("reverse_charge", "N"),
                    "B2B" if extraction.get("recipient_gstin") else "B2CS", final_type, item.get("hsn_code", ""),
                    item.get("hsn_description", ""), get_uqc_code(item.get("uqc", "OTH")), item.get("quantity", 1),
                    gst_rate, taxable_value, cgst, sgst, igst, 0, "", ""
                ]
                gs.append_to_master_ledger(business.master_ledger_sheet_id, row, sheet_name=sheet_name)
            
            _, last_index = gs.get_last_ledger_row(business.master_ledger_sheet_id, sheet_name=sheet_name)

        if tx.media_url and os.path.exists(tx.media_url):
            gs.upload_bill_image(tx.media_url, business.drive_folder_id)
            os.remove(tx.media_url)
        
        # Invoice Generation
        if final_type == "Sale" and business.invoice_template_id:
            try:
                gs.generate_sales_invoice(business.invoice_template_id, {
                    "business_name": business.business_name, "business_gstin": business.business_gstin,
                    "invoice_no": extraction.get("invoice_no", ""), "date": extracted_date,
                    "customer_name": extraction.get("customer_name", "B2C Customer"), "recipient_gstin": extraction.get("recipient_gstin", ""),
                    "hsn_code": extraction.get("hsn_code", ""), "gst_rate": extraction.get("gst_rate", 0),
                    "taxable_value": extraction.get("taxable_value", 0), "cgst": extraction.get("cgst", 0),
                    "sgst": extraction.get("sgst", 0), "igst": extraction.get("igst", 0), "total_amount": extraction.get("total_amount", 0)
                }, business.drive_folder_id)
            except Exception as inv_err: logger.warning(f"Invoice generation failed: {inv_err}")

        tx.status = "COMPLETED"
        user.last_interaction_type = "AWAITING_PAYMENT"
        user.last_interaction_data = {"row_index": last_index, "old_row": row}
        db.commit()
        
        send_whatsapp_text(user.whatsapp_id, f"✅ Recorded as {final_type}!")
        send_whatsapp_interactive(user.whatsapp_id, f"Is this {final_type} Paid or on Credit (Udhaar)?", ["Paid", "Credit"])
        return {"status": "completed"}

    except Exception as e:
        if handle_google_error(user.whatsapp_id, e): 
            return {"status": "google_error_handled"}
        logger.error(f"Error finalizing transaction {tx.id}: {e}", exc_info=True)
        tx.status = "FAILED"
        db.commit()  # Persist the failure state
        send_whatsapp_text(user.whatsapp_id, "Sorry, I encountered an error saving your transaction. Please try again.")
        return {"status": "error", "message": str(e)}

async def _handle_pdf_conversion(db: Session, user: User, business: Business, tx: Transaction):
    if tx.media_url and os.path.exists(tx.media_url):
        pdf_path = tx.media_url.replace(".jpg", ".pdf")
        if convert_image_to_pdf(tx.media_url, pdf_path):
            media_id = upload_whatsapp_media(pdf_path)
            if media_id:
                send_whatsapp_document(user.whatsapp_id, media_id, os.path.basename(pdf_path))
                send_whatsapp_text(user.whatsapp_id, "✅ Here is your PDF conversion!")
                gs = GoogleService(user.google_refresh_token)
                gs.upload_bill_image(pdf_path, business.drive_folder_id)
                os.remove(tx.media_url)
                if os.path.exists(pdf_path): os.remove(pdf_path)
                tx.status = "COMPLETED"
                db.commit()
                return {"status": "pdf_converted"}
    send_whatsapp_text(user.whatsapp_id, "Sorry, I couldn't convert that image to PDF.")
    tx.status = "FAILED"
    db.commit()
    return {"status": "pdf_failed"}

import os
import logging
import uuid
from sqlalchemy.orm import Session
from src.db_service import User, Business, Transaction
from src.utils import (
    send_whatsapp_text, send_whatsapp_interactive, get_whatsapp_media_url, 
    download_whatsapp_media, is_valid_gstin
)
from src.ai_processor import AIProcessor
from src.transcription_service import TranscriptionService
from src.consultant_agent import ConsultantAgent
from src.google_service import GoogleService

logger = logging.getLogger(__name__)

ai_processor = AIProcessor()
transcription_service = TranscriptionService()
consultant_agent = ConsultantAgent()

async def handle_command(db: Session, user: User, business: Business, message_data: dict):
    """Handles text and audio commands/messages"""
    user_whatsapp_id = user.whatsapp_id
    message_type = message_data.get("type")
    
    text = ""
    if message_type == "audio":
        audio_id = message_data.get("audio", {}).get("id")
        media_url = get_whatsapp_media_url(audio_id)
        if media_url:
            local_path = f"temp_{audio_id}.ogg"
            download_whatsapp_media(media_url, local_path)
            text, _ = transcription_service.transcribe_audio(local_path)
            if os.path.exists(local_path):
                os.remove(local_path)
        if not text:
            send_whatsapp_text(user_whatsapp_id, "Sorry, I couldn't understand that audio message.")
            return {"status": "audio_failed"}
    else:
        text = message_data.get("text", {}).get("body", "").strip()

    if not text:
        return {"status": "empty_text"}

    # 1. State Machine Handlers
    if user.last_interaction_type == "AWAITING_ADVICE" and business:
        return await _handle_awaiting_advice(db, user, business, text)
    
    elif user.last_interaction_type == "AWAITING_DUEDATE" and business:
        return await _handle_awaiting_duedate(db, user, business, text)

    elif user.last_interaction_type == "AWAITING_GSTIN":
        return await _handle_awaiting_gstin(db, user, business, text)

    elif user.last_interaction_type == "AWAITING_EDIT" and business:
        result = await _handle_awaiting_edit(db, user, business, text)
        if result: return result

    # 2. General Commands
    text_lower = text.lower()
    if text_lower == "stats" and business:
        return await _handle_stats_command(user, business)
    
    elif text_lower == "analysis" and business:
        return await _handle_analysis_command(user, business)
    
    elif text_lower == "advice":
        send_whatsapp_text(user_whatsapp_id, "I'm ready! Ask me anything about your business performance, GST, or cash flow. (e.g., 'How can I improve my margins?')")
        user.last_interaction_type = "AWAITING_ADVICE"
        db.commit()
        return {"status": "awaiting_advice"}

    elif text_lower == "switch":
        return await _handle_switch_command(db, user)

    # 3. Default: Process as a new transaction record
    return await _process_new_transaction(db, user, business, text)

async def _handle_awaiting_advice(db: Session, user: User, business: Business, text: str):
    gs = GoogleService(user.google_refresh_token)
    summary = gs.get_business_summary(business.master_ledger_sheet_id)
    advice_text = consultant_agent.analyze_business(summary, text)
    
    user.last_interaction_type = None
    db.commit()
    
    send_whatsapp_text(user.whatsapp_id, advice_text)
    return {"status": "advice_given"}

async def _handle_awaiting_duedate(db: Session, user: User, business: Business, text: str):
    if not user.last_interaction_data:
        return {"status": "error_no_data"}
    row_index = user.last_interaction_data.get("row_index")
    old_row = user.last_interaction_data.get("old_row")
    
    new_row = list(old_row)
    new_row[20] = text # Column U: Due Date
    
    gs = GoogleService(user.google_refresh_token)
    gs.update_ledger_row(business.master_ledger_sheet_id, row_index, new_row)
    
    user.last_interaction_type = None
    user.last_interaction_data = None
    db.commit()
    
    send_whatsapp_text(user.whatsapp_id, f"✅ Due date set to: *{text}*. I've updated the ledger.")
    return {"status": "duedate_completed"}

async def _handle_awaiting_gstin(db: Session, user: User, business: Business, text: str):
    if not user.last_interaction_data:
        return {"status": "error_no_data"}
    tx_id = user.last_interaction_data.get("tx_id")
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if tx:
        extraction = tx.extracted_json or {}
        final_type = tx.transaction_type or "Sale"
        if final_type == "Sale":
            extraction["recipient_gstin"] = text.strip().upper()
        else:
            extraction["vendor_gstin"] = text.strip().upper()
        
        tx.extracted_json = extraction
        tx.status = "PENDING_CONFIRM"
        user.last_interaction_type = None
        user.last_interaction_data = None
        db.commit()
        
        amount = extraction.get("total_amount", 0)
        gstin = extraction.get("recipient_gstin") if final_type == "Sale" else extraction.get("vendor_gstin")
        warning = ""
        if gstin != "N/A" and not is_valid_gstin(gstin):
            warning = "\n\n⚠️ *Warning:* The GSTIN provided looks invalid. Please verify."

        send_whatsapp_interactive(
            user.whatsapp_id,
            f"Got it! I've updated the GSTIN to {gstin}. Should I record this {final_type} for ₹{amount}?{warning}",
            ["Confirm", "Cancel"]
        )
        return {"status": "gstin_updated"}
    return {"status": "tx_not_found"}

async def _handle_awaiting_edit(db: Session, user: User, business: Business, text: str):
    if not user.last_interaction_data:
        return {"status": "error_no_data"}
    extraction = ai_processor.process_sales_text(text)
    if extraction and extraction.get("is_correction"):
        row_index = user.last_interaction_data.get("row_index")
        old_row = user.last_interaction_data.get("old_row")
        
        new_row = list(old_row)
        corrections = extraction.get("corrections", {})
        if "vendor_name" in corrections or "customer_name" in corrections:
            new_row[1] = corrections.get("vendor_name") or corrections.get("customer_name")
        if "total_amount" in corrections:
            new_row[4] = corrections.get("total_amount")
        if "date" in corrections:
            new_row[3] = corrections.get("date")
        
        gs = GoogleService(user.google_refresh_token)
        gs.update_ledger_row(business.master_ledger_sheet_id, row_index, new_row)
        
        user.last_interaction_type = None
        user.last_interaction_data = None
        db.commit()
        
        send_whatsapp_text(user.whatsapp_id, "✅ Last transaction updated successfully!")
        return {"status": "edit_completed"}
    return None

async def _handle_stats_command(user: User, business: Business):
    gs = GoogleService(user.google_refresh_token)
    summary = gs.get_business_summary(business.master_ledger_sheet_id)
    if not summary:
        send_whatsapp_text(user.whatsapp_id, "I don't have enough data yet to show stats.")
        return {"status": "no_data"}
    
    msg = (
        f"📊 *Monthly Stats for {business.business_name}*\n\n"
        f"💰 Total Sales: ₹{summary.get('total_sales', 0):,.2f}\n"
        f"💸 Total Purchases: ₹{summary.get('total_purchases', 0):,.2f}\n"
        f"🏠 Total Expenses: ₹{summary.get('total_expenses', 0):,.2f}\n"
        f"💳 Total Payments: ₹{summary.get('total_payments', 0):,.2f}\n\n"
        "Keep up the good work! 🚀"
    )
    send_whatsapp_text(user.whatsapp_id, msg)
    return {"status": "stats_sent"}

async def _handle_analysis_command(user: User, business: Business):
    gs = GoogleService(user.google_refresh_token)
    summary = gs.get_business_summary(business.master_ledger_sheet_id)
    if not summary:
        send_whatsapp_text(user.whatsapp_id, "I don't have enough data yet to perform an analysis. Record a few more bills!")
        return {"status": "no_data"}
    
    analysis_text = consultant_agent.analyze_business(summary, "Provide a general business analysis for this month.")
    send_whatsapp_text(user.whatsapp_id, analysis_text)
    return {"status": "analysis_sent"}

async def _handle_switch_command(db: Session, user: User):
    businesses = db.query(Business).filter(Business.user_whatsapp_id == user.whatsapp_id).all()
    if not businesses:
        send_whatsapp_text(user.whatsapp_id, "No businesses found linked to your account.")
        return {"status": "no_businesses"}
    
    if len(businesses) == 1:
        send_whatsapp_text(user.whatsapp_id, f"You only have one business: *{businesses[0].business_name}*.")
        return {"status": "only_one_business"}

    biz_names = [b.business_name[:20] for b in businesses[:10]]
    send_whatsapp_interactive(
        user.whatsapp_id,
        "Which business would you like to switch to?",
        biz_names
    )
    return {"status": "switch_menu_sent"}

async def _process_new_transaction(db: Session, user: User, business: Business, text: str):
    # Check if there's an existing AWAITING_DETAILS transaction
    tx = db.query(Transaction).filter(
        Transaction.user_whatsapp_id == user.whatsapp_id,
        Transaction.status == "AWAITING_DETAILS"
    ).order_by(Transaction.created_at.desc()).first()

    extraction = ai_processor.process_sales_text(text)
    if not extraction or not extraction.get("is_transaction"):
        if tx:
            # If we were awaiting details, maybe this text *is* the detail but AI failed to parse as full tx?
            send_whatsapp_text(user.whatsapp_id, "I couldn't quite understand that. Please type the details clearly (e.g., 'Sold 500 worth of items').")
            return {"status": "awaiting_details_retry"}

        # Handle non-transactional messages or greetings not caught by orchestrator
        # Instead of just saying "not sure", let's offer the main menu
        send_whatsapp_interactive(
            user.whatsapp_id,
            "I'm not sure how to handle that. How can I help you? 🚀",
            ["💰 Money In", "💸 Money Out", "🛠️ Business Tools"]
        )
        return {"status": "main_menu_offered"}

    if tx:
        # Update existing transaction
        tx.extracted_json = extraction
        if extraction.get("transaction_type") and extraction.get("transaction_type") != "PENDING":
             tx.transaction_type = extraction.get("transaction_type")
        
        if tx.transaction_type == "Expense":
             tx.status = "PENDING_CONFIRM"
        else:
             tx.status = "PENDING_SUBTYPE"
    else:
        # Cancel old pending transactions to avoid collisions
        db.query(Transaction).filter(
            Transaction.user_whatsapp_id == user.whatsapp_id,
            Transaction.status.in_(["PENDING_TYPE", "PENDING_SUBTYPE", "PENDING_CONFIRM"])
        ).update({"status": "CANCELLED"})

        # Store as a new pending transaction
        tx_type = extraction.get("transaction_type", "Sale")
        tx = Transaction(
            id=str(uuid.uuid4()),
            user_whatsapp_id=user.whatsapp_id,
            business_id=business.id,
            transaction_type=tx_type,
            extracted_json=extraction,
            status="PENDING_TYPE"
        )
        db.add(tx)
    
    db.commit()

    if tx.status == "PENDING_TYPE":
        # If it was a fresh tx, we ask for the bucket
        send_whatsapp_interactive(
            user.whatsapp_id,
            f"I've detected a possible *{tx.transaction_type}*. Which category does this belong to?",
            ["💰 Money In", "💸 Money Out", "Cancel"]
        )
        return {"status": "awaiting_type_bucket"}
    else:
        # If it was AWAITING_DETAILS, it already has a type/bucket context
        if tx.transaction_type in ["Sale", "Purchase"]:
            send_whatsapp_interactive(
                user.whatsapp_id,
                f"Is this a B2B {tx.transaction_type} (with GSTIN) or B2C (without GSTIN)?",
                ["B2B", "B2C"]
            )
            return {"status": "awaiting_subtype"}
        elif tx.transaction_type == "Payment":
             send_whatsapp_interactive(
                user.whatsapp_id,
                "Is this a One-time (Single) payment or a Recurring payment?",
                ["Single", "Recurring"]
            )
             return {"status": "awaiting_subtype"}
        else:
             from src.bot.handlers.interactive import _handle_confirmation
             return await _handle_confirmation(db, user, business, tx, "Initial")

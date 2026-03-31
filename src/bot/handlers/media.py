import os
import logging
import uuid
from sqlalchemy.orm import Session
from src.db_service import User, Business, Transaction
from src.utils import (
    get_whatsapp_media_url, download_whatsapp_media, send_whatsapp_interactive, send_whatsapp_text
)

logger = logging.getLogger(__name__)

async def handle_media(db: Session, user: User, business: Business, message_data: dict):
    """Handles incoming media (images or documents) from WhatsApp"""
    user_whatsapp_id = user.whatsapp_id
    message_type = message_data.get("type")
    
    logger.info(f"Received media message type: {message_type} from {user_whatsapp_id}")

    if message_type in ["image", "document"]:
        # 1. Download Media
        media_id = message_data.get(message_type, {}).get("id")
        filename = message_data.get(message_type, {}).get("filename", f"media_{media_id}")
        
        # If it's a document, check if it's an image or PDF
        if message_type == "document":
            mime_type = message_data.get("document", {}).get("mime_type", "")
            if not (mime_type.startswith("image/") or mime_type == "application/pdf"):
                logger.warning(f"Unsupported document type: {mime_type}")
                return {"status": "unsupported_document"}

        logger.info(f"Processing media_id: {media_id} ({message_type})")
        
        media_url = get_whatsapp_media_url(media_id)
        if media_url:
            ext = ".jpg"
            if message_type == "document" and "." in filename:
                ext = f".{filename.split('.')[-1]}"
            
            local_path = os.path.join("temp_media", f"media_{media_id}{ext}")
            download_whatsapp_media(media_url, local_path)
            logger.info(f"Media downloaded to: {local_path}")
            
            # Check for existing AWAITING_DETAILS transaction
            tx = db.query(Transaction).filter(
                Transaction.user_whatsapp_id == user_whatsapp_id,
                Transaction.status == "AWAITING_DETAILS"
            ).order_by(Transaction.created_at.desc()).first()

            if tx:
                logger.info(f"Found pending transaction {tx.id} with status AWAITING_DETAILS for user {user_whatsapp_id}")
                tx.media_url = local_path
                tx.status = "PENDING_SUBTYPE" 
                db.commit()
                
                if tx.transaction_type in ["Sale", "Purchase"]:
                    send_whatsapp_interactive(
                        user_whatsapp_id,
                        f"I've received the bill for this {tx.transaction_type}. Is it B2B or B2C?",
                        ["B2B", "B2C"]
                    )
                elif tx.transaction_type == "Payment":
                    send_whatsapp_interactive(
                        user_whatsapp_id,
                        "I've received the document for this Payment. Is it a Single or Recurring payment?",
                        ["Single", "Recurring"]
                    )
                else:
                    from src.bot.handlers.interactive import _handle_confirmation
                    return await _handle_confirmation(db, user, business, tx, "Initial")
                
                return {"status": "awaiting_subtype"}

            logger.info("No AWAITING_DETAILS transaction found, creating new PENDING_TYPE transaction")
            # Cancel old pending transactions to avoid collisions
            db.query(Transaction).filter(
                Transaction.user_whatsapp_id == user_whatsapp_id,
                Transaction.status.in_(["PENDING_TYPE", "PENDING_SUBTYPE", "PENDING_CONFIRM"])
            ).update({"status": "CANCELLED"})

            # 2. Store pending transaction in DB
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

            # 3. Ask user for type via Buttons/List
            send_whatsapp_interactive(
                user_whatsapp_id, 
                f"I've received your image for {business.business_name}! 📸 Which category does this belong to?",
                ["💰 Money In", "💸 Money Out", "Cancel"]
            )
            return {"status": "awaiting_type_bucket"}
        else:
            logger.error(f"Failed to get media URL for {media_id}")
            send_whatsapp_text(user_whatsapp_id, "Sorry, I had trouble downloading that file. Please try again.")
            return {"status": "media_url_failed"}
    
    return {"status": "unsupported_media"}

import os
import logging
import uuid
from sqlalchemy.orm import Session
from src.db_service import User, Business, Transaction
from src.utils import (
    get_whatsapp_media_url, download_whatsapp_media, send_whatsapp_interactive
)

logger = logging.getLogger(__name__)

async def handle_media(db: Session, user: User, business: Business, message_data: dict):
    """Handles incoming media (images) from WhatsApp"""
    user_whatsapp_id = user.whatsapp_id
    message_type = message_data.get("type")

    if message_type == "image":
        # 1. Download Media
        image_id = message_data.get("image", {}).get("id")
        media_url = get_whatsapp_media_url(image_id)
        if media_url:
            local_path = f"temp_{image_id}.jpg"
            download_whatsapp_media(media_url, local_path)
            
            # Check for existing AWAITING_DETAILS transaction
            tx = db.query(Transaction).filter(
                Transaction.user_whatsapp_id == user_whatsapp_id,
                Transaction.status == "AWAITING_DETAILS"
            ).order_by(Transaction.created_at.desc()).first()

            if tx:
                tx.media_url = local_path
                tx.status = "PENDING_SUBTYPE" # Or proceed to confirmation
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
    
    return {"status": "unsupported_media"}

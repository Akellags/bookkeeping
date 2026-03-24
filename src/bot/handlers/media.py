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
                f"I've received your image for {business.business_name}! 📸 What would you like to do?",
                ["Sale", "Purchase", "Expense", "Payment", "Convert to PDF"]
            )
            return {"status": "awaiting_type"}
    
    return {"status": "unsupported_media"}

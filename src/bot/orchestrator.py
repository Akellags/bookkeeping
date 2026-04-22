import os
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError
from src.db_service import User, Business, Transaction, ProcessedMessage
from src.google_service import GoogleService
from src.utils import send_whatsapp_text, send_whatsapp_interactive
from src.bot.handlers.commands import handle_command
from src.bot.handlers.media import handle_media
from src.bot.handlers.interactive import handle_interactive

logger = logging.getLogger(__name__)

class WhatsAppOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    async def handle_payload(self, payload: dict):
        """Orchestrates the processing of a WhatsApp webhook payload"""
        try:
            entries = payload.get("entry", [])
            if not entries:
                return {"status": "no entry"}
            
            results = []
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages_list = value.get("messages", [])
                    
                    if not messages_list:
                        # Could be a status update, not a message
                        statuses = value.get("statuses", [])
                        if statuses:
                            status = statuses[0]
                            logger.info(f"Orchestrator: Received status update '{status.get('status')}' for ID: {status.get('id')}")
                            results.append({"status": "status_update"})
                            continue
                        
                        logger.info(f"Orchestrator: No messages or statuses in change value. Keys: {list(value.keys())}")
                        results.append({"status": "no_messages"})
                        continue

                    for message_data in messages_list:
                        message_id = message_data.get("id")
                        user_whatsapp_id = str(message_data.get("from"))
                        message_type = message_data.get("type")
                        
                        logger.info(f"Orchestrator: Handling message from {user_whatsapp_id} | Type: {message_type} | ID: {message_id}")
                        # Added for deep debugging
                        logger.info(f"FULL MESSAGE DATA: {message_data}")

                        # 1. Idempotency Check (Atomic via DB constraint)
                        if message_id:
                            try:
                                from src.db_service import ProcessedMessage # Inline to avoid circular if any
                                from sqlalchemy.exc import IntegrityError
                                
                                new_msg = ProcessedMessage(message_id=message_id)
                                self.db.add(new_msg)
                                self.db.commit()
                            except IntegrityError:
                                self.db.rollback()
                                logger.info(f"Skipping already processed message: {message_id}")
                                continue
                            except Exception as e:
                                self.db.rollback()
                                # Check if it's a duplicate key error even if not caught by IntegrityError
                                if "duplicate key" in str(e).lower() or "23505" in str(e):
                                    logger.info(f"Message already processed (detected via string match), skipping: {message_id}")
                                    continue
                                logger.error(f"Database error in idempotency check: {e}")
                                # Continue processing anyway if it's not a duplicate constraint

                        # 2. Extract text body if available
                        text_body = ""
                        if message_type == "text":
                            text_body = message_data.get("text", {}).get("body", "").strip()

                        # 3. Handle High Priority Greetings/Menu
                        if text_body and text_body.lower() in ["hi", "hello", "hey", "help", "menu"]:
                            results.append(await self._send_menu(user_whatsapp_id))
                            continue

                        # 4. Handle Link/Verification Codes
                        if text_body and (text_body.upper().startswith("VERIFY_") or (len(text_body) == 6 and all(c in "0123456789ABCDEFabcdef" for c in text_body))):
                            result = await self._handle_verification(user_whatsapp_id, text_body)
                            if result: 
                                results.append(result)
                                continue

                        # 5. Check if user is linked
                        user = self.db.query(User).filter(User.whatsapp_id == user_whatsapp_id).first()
                        if not user or not user.google_refresh_token:
                            results.append(await self._send_onboarding(user_whatsapp_id))
                            continue

                        # 6. Get active business
                        business = self.db.query(Business).filter(Business.id == user.active_business_id).first()
                        if not business:
                            business = self.db.query(Business).filter(Business.user_whatsapp_id == user.whatsapp_id).first()

                        if not business:
                            from src.utils import send_whatsapp_text
                            send_whatsapp_text(user_whatsapp_id, "Please set up your business profile first on the Help U dashboard.")
                            results.append({"status": "business_not_set"})
                            continue

                        # 7. Lazy Drive Initialization
                        if not user.drive_initialized:
                            try:
                                logger.info(f"Lazily initializing Google Drive for user {user_whatsapp_id}")
                                gs = GoogleService(user.google_refresh_token)
                                folder_id, sheet_id, template_id = await gs.initialize_user_drive()
                                
                                # Ensure business has correct IDs
                                business.drive_folder_id = folder_id
                                business.master_ledger_sheet_id = sheet_id
                                if template_id:
                                    business.invoice_template_id = template_id
                                
                                user.drive_initialized = True
                                self.db.commit()
                            except Exception as e:
                                logger.error(f"Lazy drive initialization failed for {user_whatsapp_id}: {e}")

                        # 8. Delegate to specific handlers
                        try:
                            logger.info(f"Delegating message of type {message_type} to handler")
                            if message_type in ["text", "audio"]:
                                results.append(await handle_command(self.db, user, business, message_data))
                            elif message_type in ["image", "document"]:
                                logger.info(f"Orchestrator: Routing to handle_media for {message_type}")
                                results.append(await handle_media(self.db, user, business, message_data))
                            elif message_type == "interactive":
                                results.append(await handle_interactive(self.db, user, business, message_data))
                            else:
                                logger.warning(f"Unsupported message type: {message_type}")
                                results.append({"status": "unsupported_type"})
                        except Exception as e:
                            logger.error(f"Error delegating message {message_id}: {e}", exc_info=True)
                            results.append({"status": "handler_error", "error": str(e)})
            
            return results

        except Exception as e:
            logger.error(f"CRITICAL ERROR in WhatsAppOrchestrator: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _send_menu(self, user_whatsapp_id: str):
        # Clear state if any
        db_user = self.db.query(User).filter(User.whatsapp_id == user_whatsapp_id).first()
        if db_user:
            db_user.last_interaction_type = None
            db_user.last_interaction_data = None
            # Cancel any pending transactions to avoid flow collisions
            self.db.query(Transaction).filter(
                Transaction.user_whatsapp_id == user_whatsapp_id,
                Transaction.status.in_(["PENDING_TYPE", "PENDING_SUBTYPE", "PENDING_CONFIRM"])
            ).update({"status": "CANCELLED"})
            self.db.commit()

        menu_msg = (
            "Hello! 👋 I'm your Help U bookkeeping assistant.\n\n"
            "How can I help you today? 🚀"
        )
        logger.info(f"Sending high-level menu to {user_whatsapp_id}")
        send_whatsapp_interactive(
            user_whatsapp_id, 
            menu_msg, 
            ["💰 Money In", "💸 Money Out", "🛠️ Business Tools"]
        )
        return {"status": "main_menu_sent"}

    async def _handle_verification(self, user_whatsapp_id: str, text_body: str):
        token = text_body.split("_")[-1].upper() if text_body.upper().startswith("VERIFY_") else text_body.upper()
        
        web_user = self.db.query(User).filter(
            User.link_token == token,
            User.link_token_expires_at > datetime.utcnow()
        ).first()
        
        if web_user:
            old_web_id = web_user.whatsapp_id
            existing_real_user = self.db.query(User).filter(User.whatsapp_id == user_whatsapp_id).first()
            
            if existing_real_user:
                existing_real_user.google_email = web_user.google_email
                existing_real_user.google_refresh_token = web_user.google_refresh_token
                existing_real_user.active_business_id = web_user.active_business_id
                self.db.delete(web_user)
            else:
                new_user = User(
                    whatsapp_id=user_whatsapp_id,
                    google_email=web_user.google_email,
                    google_refresh_token=web_user.google_refresh_token,
                    active_business_id=web_user.active_business_id,
                    subscription_status=web_user.subscription_status
                )
                self.db.add(new_user)
                self.db.delete(web_user)
            
            self.db.commit()
            self.db.query(Business).filter(Business.user_whatsapp_id == old_web_id).update({"user_whatsapp_id": user_whatsapp_id})
            self.db.query(Transaction).filter(Transaction.user_whatsapp_id == old_web_id).update({"user_whatsapp_id": user_whatsapp_id})
            self.db.commit()

            send_whatsapp_text(user_whatsapp_id, "✅ Success! Your WhatsApp is now linked to your Help U account. You can start sending me bills now! 🚀")
            await self._send_menu(user_whatsapp_id)
            return {"status": "linked_successfully"}
        
        if text_body.upper().startswith("VERIFY_"):
            send_whatsapp_text(user_whatsapp_id, "❌ Invalid or expired verification code. Please check the code on your dashboard and try again.")
            return {"status": "invalid_token"}
        
        return None

    async def _send_onboarding(self, user_whatsapp_id: str):
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
        base_url = redirect_uri.split('/auth/callback')[0]
        onboarding_url = f"{base_url}/auth/google?whatsapp_id={user_whatsapp_id}"
        
        msg = (
            "Welcome to Help U! 🚀\n\n"
            "I see you haven't linked your Google Drive yet. Please click the link below to authorize me "
            "so I can start recording your bills and sales:\n\n"
            f"{onboarding_url}\n\n"
            "💡 *Already signed up on the web?* Just reply with the 6-digit 'Link Code' from your dashboard."
        )
        send_whatsapp_text(user_whatsapp_id, msg)
        return {"status": "onboarding_sent"}

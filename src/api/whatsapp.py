import os
import logging
from fastapi import APIRouter, Request, HTTPException, Query, Depends, Response, BackgroundTasks
from sqlalchemy.orm import Session
from src.db_service import get_db, SessionLocal
from src.bot.orchestrator import WhatsAppOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# WhatsApp Webhook Verification Token
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
if not VERIFY_TOKEN:
    logger.warning("WHATSAPP_VERIFY_TOKEN not set in environment!")

@router.get("/webhook")
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

async def process_background_payload(payload: dict):
    """Processes WhatsApp payload in the background to avoid webhook timeouts"""
    db = SessionLocal()
    try:
        orchestrator = WhatsAppOrchestrator(db)
        await orchestrator.handle_payload(payload)
    except Exception as e:
        logger.error(f"Error processing background payload: {e}", exc_info=True)
    finally:
        db.close()

@router.post("/webhook")
async def handle_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming WhatsApp messages and media"""
    payload = await request.json()
    
    # Sanitize logging: extract basic info without sensitive message content
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if messages:
            msg = messages[0]
            logger.info(f"Received WhatsApp message from {msg.get('from')} (ID: {msg.get('id')})")
        else:
            logger.info(f"Received WhatsApp webhook: {payload.get('object')}")
    except Exception:
        logger.info("Received WhatsApp webhook with unexpected format")
    
    # Process in background and return 200 OK immediately to WhatsApp
    background_tasks.add_task(process_background_payload, payload)
    return {"status": "accepted"}

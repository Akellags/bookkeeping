import os
import logging
import json
import traceback
from fastapi import APIRouter, Request, HTTPException, Query, Depends, Response, BackgroundTasks
from sqlalchemy.orm import Session
from src.db_service import get_db, SessionLocal
from src.bot.orchestrator import WhatsAppOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """WhatsApp Webhook Verification"""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN") or os.getenv("WEBHOOK_VERIFY_TOKEN")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    else:
        logger.error(f"Webhook verification failed. Expected: {verify_token}, Got: {hub_verify_token}")
        raise HTTPException(status_code=403, detail="Verification failed")

async def process_background_payload(payload: dict):
    """Processes WhatsApp payload in the background to avoid webhook timeouts"""
    logger.info("Starting background processing of WhatsApp payload")
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
    try:
        body = await request.body()
        payload = json.loads(body)
        logger.info(f"RAW WEBHOOK PAYLOAD: {body.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Error parsing raw webhook body: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    
    # Process in background and return 200 OK immediately to WhatsApp
    background_tasks.add_task(process_background_payload, payload)

    # Sanitize logging: extract basic info without sensitive message content
    try:
        entries = payload.get("entry", [])
        if not entries:
            logger.info(f"Received empty WhatsApp webhook payload object: {payload.get('object')}")
            return {"status": "accepted"}

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Check for messages
                messages = value.get("messages", [])
                if messages:
                    for msg in messages:
                        logger.info(f"Received WhatsApp message from {msg.get('from')} (ID: {msg.get('id')}) type: {msg.get('type')}")
                        if msg.get('type') in ["image", "document"]:
                            logger.info(f"Media details: {msg.get(msg.get('type'))}")
                
                # Check for statuses
                statuses = value.get("statuses", [])
                if statuses:
                    for status in statuses:
                        status_name = status.get('status')
                        status_id = status.get('id')
                        error_details = status.get('errors')
                        logger.info(f"Received WhatsApp status update: {status_name} for ID: {status_id}")
                        if error_details:
                            logger.error(f"STATUS ERROR for {status_id}: {error_details}")
                        if status_name == "failed":
                            logger.error(f"FULL FAILED PAYLOAD for {status_id}: {status}")
                
                if not messages and not statuses:
                    logger.info(f"Received WhatsApp webhook (object: {payload.get('object')}) with value: {value}")
                    
    except Exception as e:
        logger.error(f"Error logging WhatsApp webhook: {e}")
    
    return {"status": "accepted"}

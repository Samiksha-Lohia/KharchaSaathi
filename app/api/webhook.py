import os
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks, Query
from fastapi.responses import Response, JSONResponse
from app.services.redis_service import is_duplicate_message
from app.agents.agent_pipeline import process_whatsapp_message

logger = logging.getLogger(__name__)
router = APIRouter()

# Webhook secret configurations
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "kharchasaathi_verify_token")
APP_SECRET = os.getenv("META_APP_SECRET", "")  # Used to sign payloads with HMAC SHA256

def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """
    Verifies that the payload was signed by Meta using the App Secret.
    """
    if not APP_SECRET:
        # If no secret is configured, warn and bypass verification to simplify local testing
        logger.warning("META_APP_SECRET is not set. Bypassing webhook signature verification.")
        return True

    if not signature_header:
        logger.error("Missing X-Hub-Signature-256 header.")
        return False

    try:
        # Signature format is: sha256=HEX_DIGEST
        if not signature_header.startswith("sha256="):
            return False
        
        expected_sig = signature_header.split("sha256=")[1]
        actual_sig = hmac.new(
            APP_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(actual_sig, expected_sig)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    challenge: str = Query(None, alias="hub.challenge"),
    token: str = Query(None, alias="hub.verify_token")
):
    """
    Verification endpoint for Meta WhatsApp Cloud API subscription.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.warning("Webhook verification failed. Invalid token.")
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256")
):
    """
    Webhook endpoint to receive real-time updates from Meta WhatsApp Cloud API.
    Acks with 200 OK immediately and processes message in background.
    """
    raw_body = await request.body()
    
    # 1. Verify Meta signature
    if not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Error parsing JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    # 2. Extract message details from payload structure
    # Expected format: entry[] -> changes[] -> value -> messages[]
    try:
        entry = payload.get("entry", [])
        if not entry:
            return JSONResponse(status_code=200, content={"status": "no entries"})
            
        changes = entry[0].get("changes", [])
        if not changes:
            return JSONResponse(status_code=200, content={"status": "no changes"})
            
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            # WhatsApp sends statuses updates too (e.g. read, delivered). We ack and ignore them.
            return JSONResponse(status_code=200, content={"status": "status_update_ack"})
            
        message = messages[0]
        message_id = message.get("id")
        sender_phone = message.get("from")
        
        # 3. Deduplicate messages
        if is_duplicate_message(message_id):
            logger.info(f"Duplicate message ignored: {message_id}")
            return JSONResponse(status_code=200, content={"status": "duplicate_ignored"})
            
        # 4. Dispatch processing to background thread/task
        background_tasks.add_task(
            process_whatsapp_message,
            payload=payload,
            sender_phone=sender_phone,
            message=message
        )
        
        # Return immediate 200 OK response to Meta (expects response < 20s)
        return JSONResponse(status_code=200, content={"status": "accepted"})
        
    except Exception as e:
        logger.error(f"Error parsing WhatsApp payload fields: {e}")
        # Return 200 to prevent WhatsApp from disabling the webhook on random code exceptions
        return JSONResponse(status_code=200, content={"status": "error_parsed_but_acked"})

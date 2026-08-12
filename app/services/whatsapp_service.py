import os
import logging
import httpx

logger = logging.getLogger(__name__)

META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")

def send_whatsapp_message(to_phone: str, text: str):
    """
    Sends a text message using Meta WhatsApp Cloud API.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning("META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID not set. Skipping send_whatsapp_message.")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "body": text
        }
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if response.status_code == 200:
            logger.info(f"WhatsApp message successfully sent to {to_phone}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp message. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error calling Meta WhatsApp send message API: {e}")
        return False

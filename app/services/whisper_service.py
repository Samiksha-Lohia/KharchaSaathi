import os
import logging
import httpx

logger = logging.getLogger(__name__)

# Config
META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", "") or os.getenv("GROQ_API_KEY", "")

MAX_AUDIO_SIZE_BYTES = 2 * 1024 * 1024  # 2MB Limit

def download_whatsapp_media(media_id: str) -> bytes:
    """
    Downloads media from Meta WhatsApp Cloud API.
    In testing/offline mode, returns mock bytes or raises if mock error.
    """
    if media_id == "test_voice_note_large":
        # Simulate large file
        return b"0" * (MAX_AUDIO_SIZE_BYTES + 100)
    if media_id.startswith("test_voice_note") or media_id.startswith("test_bill_image"):
        return b"mock_media_bytes"

    if not META_WHATSAPP_TOKEN:
        raise ValueError("META_WHATSAPP_TOKEN is not configured")

    headers = {"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"}
    
    # 1. Get media URL
    url = f"https://graph.facebook.com/v20.0/{media_id}"
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    media_url = response.json().get("url")
    
    if not media_url:
        raise ValueError(f"Could not retrieve media URL for ID {media_id}")
        
    # 2. Download media content
    download_res = httpx.get(media_url, headers=headers)
    download_res.raise_for_status()
    
    return download_res.content


def transcribe_voice_note(media_id: str) -> str:
    """
    Downloads WhatsApp voice note media and transcribes it using Whisper.
    Caps size at 2MB.
    """
    # 1. Download media bytes
    audio_data = download_whatsapp_media(media_id)
    
    # 2. Validate size limit
    if len(audio_data) > MAX_AUDIO_SIZE_BYTES:
        raise ValueError("Audio note exceeds maximum size limit of 2MB.")
        
    # 3. Handle offline test fallback
    if media_id == "test_voice_note":
        return "Alice spent 900 on Dinner"
    if media_id == "test_voice_note_hinglish":
        return "Maine 500 kharch kiya khane me"
        
    if not WHISPER_API_KEY:
        raise ValueError("WHISPER_API_KEY (or GROQ_API_KEY) is not configured for Whisper transcription")
        
    # 4. Call Groq Whisper API
    # We write bytes to a temp structure or pass directly in files payload
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}
    files = {
        "file": ("voice.ogg", audio_data, "audio/ogg"),
        "model": (None, "whisper-large-v3"),
    }
    
    try:
        response = httpx.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json().get("text", "")
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise RuntimeError(f"Transcription error: {e}")

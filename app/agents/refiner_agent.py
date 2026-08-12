import os
import re
import json
import logging

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

def refine_response_fallback(raw_result: str) -> str:
    """
    Deterministic backup formatter converting all paise units to rupees.
    E.g. "1200 paise" -> "₹12".
    """
    def replace_paise(match):
        paise_val = int(match.group(1))
        rupee_val = paise_val / 100.0
        if rupee_val.is_integer():
            return f"₹{int(rupee_val)}"
        return f"₹{rupee_val:.2f}"
        
    refined = re.sub(r"(\d+)\s*paise", replace_paise, raw_result)
    return refined


def refine_response(raw_result: str) -> str:
    """
    Refines raw database results into conversational Hinglish using Groq LLM.
    Converts all paise to Rupees.
    """
    if not GROQ_API_KEY:
        return refine_response_fallback(raw_result)
        
    system_prompt = """
    You are the response refiner agent for KharchaSaathi, an expense sharing WhatsApp bot.
    Your task is to take a raw/dry database tool execution result message, rewrite it into friendly, conversational Hinglish (Hindi + English) suitable for a group chat, and format all money values.
    
    CRITICAL RULES:
    1. Convert all paise values into Rupees (divide the paise amount by 100, and format with the ₹ symbol). E.g. "1200 paise" should become "₹12", "5000 paise" should become "₹50".
    2. Make the message casual, cheeky, and under 3 sentences. Keep it friendly like a group roommate.
    3. Do NOT add extra info. Preserve the names, items, and math exactly.
    """
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Refine this raw result: '{raw_result}'"}
            ],
            temperature=0.3
        )
        refined_text = completion.choices[0].message.content.strip()
        if refined_text:
            return refined_text
            
    except Exception as e:
        logger.warning(f"Groq Response Refiner failed ({e}). Falling back to rule-based formatter.")
        
    return refine_response_fallback(raw_result)

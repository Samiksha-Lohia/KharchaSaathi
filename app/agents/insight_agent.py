import os
import logging
from sqlalchemy.orm import Session
from app.services.redis_service import redis_client, use_fallback

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
NUDGE_RATE_LIMIT_TTL = 3 * 24 * 60 * 60  # 3 days

def check_nudge_rate_limit(group_id: int) -> bool:
    """
    Checks if a nudge was already sent to the group within the rate limit window.
    Returns True if allowed (no nudge sent recently), False otherwise.
    """
    key = f"nudge_limit:{group_id}"
    try:
        # Check if rate limit key exists
        if use_fallback:
            is_new = redis_client.set_nx(key, "active", ex=NUDGE_RATE_LIMIT_TTL)
            return is_new
        else:
            res = redis_client.set(key, "active", ex=NUDGE_RATE_LIMIT_TTL, nx=True)
            return res is True or res == "OK"
    except Exception as e:
        logger.error(f"Redis rate limit check error: {e}")
        return True  # Fallback to allowing in case of cache issues


def is_group_muted(group_id: int) -> bool:
    """
    Checks if nudges are muted for the group.
    Uses Redis key nudge_mute:{group_id}.
    """
    key = f"nudge_mute:{group_id}"
    try:
        val = redis_client.get(key)
        return val is not None
    except Exception as e:
        logger.error(f"Redis mute check error: {e}")
        return False


def mute_group_nudges(group_id: int, duration_seconds: int = 30 * 24 * 60 * 60):
    """
    Mutes nudges for a group (default 30 days).
    """
    key = f"nudge_mute:{group_id}"
    try:
        redis_client.set(key, "muted", ex=duration_seconds)
    except Exception as e:
        logger.error(f"Redis set mute error: {e}")


def generate_insight_text_fallback(nudge_type: str, data: dict) -> str:
    """
    Deterministic phrasing backup function for offline tests.
    """
    if nudge_type == "overdue_settlements":
        debts = data.get("debts", [])
        lines = ["Oi! Yeh settlement overdue hai:"]
        for d in debts:
            lines.append(f"- {d['debtor_name']} owes {d['creditor_name']} {d['amount']} paise for {d['days_overdue']} days")
        return "\n".join(lines)
        
    elif nudge_type == "weekly_spending":
        total = data.get("total_spending", 0)
        count = data.get("expenses_count", 0)
        return f"Weekly Insight: Group spent total {total} paise across {count} expenses this week. Achhi bachat ki!"
        
    elif nudge_type == "inactivity":
        days = data.get("days_inactive", 0)
        name = data.get("group_name", "group")
        return f"Group '{name}' has been inactive for {days} days. Koi kharch nahi hai?"
        
    elif nudge_type == "month_end_settlement":
        debts = data.get("debts", [])
        if not debts:
            return "Month-end check: All settled up!"
        lines = ["Month-end check! Chalo settle up karein:"]
        for d in debts:
            lines.append(f"- {d['debtor_name']} -> {d['creditor_name']}: {d['amount']} paise")
        return "\n".join(lines)
        
    return "Oi! Check your KharchaSaathi dashboard!"


def generate_insight_text_llm(nudge_type: str, data: dict) -> str:
    """
    Calls Groq LLM to phrase statistics into a natural Hinglish nudge.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")
        
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    
    system_prompt = """
    You are the phrasing agent of KharchaSaathi. Your job is to translate dry financial stats into a friendly, humorous, and direct Hinglish (Hindi + English) WhatsApp nudge for a group chat. 
    Keep the tone conversational, slightly cheeky (like a group friend), and under 3 sentences.
    Always format monetary units in rupees (divide paise values by 100).
    """
    
    user_prompt = f"Format this periodic insight report. Type: '{nudge_type}', Data: {data}"
    
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    return completion.choices[0].message.content


def generate_and_send_nudge(db: Session, group_id: int, nudge_type: str, data: dict):
    """
    Checks rate-limiting and mute state, generates natural language nudge text,
    and logs/sends the outgoing message.
    """
    # 1. Check if group is muted
    if is_group_muted(group_id):
        logger.info(f"Group {group_id} is muted. Nudge skipped.")
        return
        
    # 2. Check rate limit
    if not check_nudge_rate_limit(group_id):
        logger.info(f"Group {group_id} has already been nudged recently. Skipping.")
        return

    # 3. Generate nudge text
    try:
        nudge_text = generate_insight_text_llm(nudge_type, data)
    except Exception as e:
        logger.warning(f"LLM insight generation failed ({e}). Using fallback.")
        nudge_text = generate_insight_text_fallback(nudge_type, data)
        
    # 4. Deliver nudge to group
    # Log the output response
    logger.info(f"SENDING PROACTIVE NUDGE to group {group_id}:\n{nudge_text}")
    # (Here you would call whatsapp_service.py to send actual message)

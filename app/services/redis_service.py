import os
import json
import time
import logging
import redis

logger = logging.getLogger(__name__)

# Fallback in-memory storage for offline development/testing
class MemoryCache:
    def __init__(self):
        self.data = {}
        self.expires = {}

    def _cleanup(self):
        now = time.time()
        expired_keys = [k for k, exp in self.expires.items() if exp < now]
        for k in expired_keys:
            self.data.pop(k, None)
            self.expires.pop(k, None)

    def get(self, key):
        self._cleanup()
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self._cleanup()
        self.data[key] = value
        if ex:
            self.expires[key] = time.time() + ex
        else:
            self.expires.pop(key, None)

    def set_nx(self, key, value, ex=None):
        self._cleanup()
        if key in self.data:
            return False
        self.set(key, value, ex)
        return True

    def delete(self, key):
        self.data.pop(key, None)
        self.expires.pop(key, None)


# Read Redis URL configuration
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None
use_fallback = False

try:
    redis_client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
    # Test connection
    redis_client.ping()
    logger.info("Connected to Redis successfully.")
except Exception as e:
    logger.warning(f"Failed to connect to Redis ({e}). Falling back to in-memory cache.")
    use_fallback = True
    redis_client = MemoryCache()


def is_duplicate_message(msg_id: str) -> bool:
    """
    Checks if message ID was already processed.
    Uses redis key msg_dedup:{msg_id} with 24h TTL.
    """
    key = f"msg_dedup:{msg_id}"
    try:
        if use_fallback:
            is_new = redis_client.set_nx(key, "processed", ex=86400)
            return not is_new
        else:
            # set NX=True returns True if set, False if key already exists
            res = redis_client.set(key, "processed", ex=86400, nx=True)
            return res is None or res is False
    except Exception as e:
        logger.error(f"Redis error in is_duplicate_message: {e}. Defaulting to duplicate=False.")
        return False


def acquire_group_lock(group_id: int) -> bool:
    """
    Acquires a concurrency lock for a group.
    Uses session_lock:{group_id} with 30s TTL.
    """
    key = f"session_lock:{group_id}"
    try:
        if use_fallback:
            return redis_client.set_nx(key, "locked", ex=30)
        else:
            res = redis_client.set(key, "locked", ex=30, nx=True)
            return res is True or res == "OK"
    except Exception as e:
        logger.error(f"Redis lock error: {e}. Defaulting to lock acquired.")
        return True


def release_group_lock(group_id: int):
    """
    Releases the concurrency lock for a group.
    """
    key = f"session_lock:{group_id}"
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis unlock error: {e}")


def set_pending_action(user_id: int, action_data: dict):
    """
    Caches an ambiguous or OCR action pending confirmation from a user.
    Uses pending_confirm:{user_id} with 5m TTL.
    """
    key = f"pending_confirm:{user_id}"
    try:
        val = json.dumps(action_data)
        redis_client.set(key, val, ex=300)
    except Exception as e:
        logger.error(f"Redis set pending action error: {e}")


def get_pending_action(user_id: int) -> dict | None:
    """
    Retrieves the pending action context for a user.
    """
    key = f"pending_confirm:{user_id}"
    try:
        val = redis_client.get(key)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            return json.loads(val)
    except Exception as e:
        logger.error(f"Redis get pending action error: {e}")
    return None


def clear_pending_action(user_id: int):
    """
    Clears the cached pending action for a user.
    """
    key = f"pending_confirm:{user_id}"
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis delete pending action error: {e}")

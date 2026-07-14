"""bot/state.py — State management for the personal assistant bot."""
import os
import json
import logging
import tempfile
from config import STATE_FILE

import asyncio
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

# In-memory locks per user to allow concurrent bot usage by different users
user_locks = defaultdict(asyncio.Lock)

# Global lock for state file operations to prevent race conditions
_state_lock = threading.Lock()

def get_user_lock(chat_id: int) -> asyncio.Lock:
    return user_locks[chat_id]


def get_hash(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def is_sleep_window() -> bool:
    """Returns True if current time is between 1 AM and 7 AM Eastern Time."""
    try:
        import datetime
        from zoneinfo import ZoneInfo
        et_tz = ZoneInfo('America/New_York')
        now_et = datetime.datetime.now(datetime.timezone.utc).astimezone(et_tz)
        return 1 <= now_et.hour < 7
    except Exception:
        return False


def load_state() -> dict:
    """Load bot state from state.json with thread safety."""
    with _state_lock:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                if "pending_priorities" not in state:
                    state["pending_priorities"] = {}
                if "user_models" not in state:
                    state["user_models"] = {}
                return state
    return {"seen_tasks": [], "seen_alerts": [], "pending_priorities": {}, "user_models": {}}


def save_state(state):
    """Atomic write state.json (temp file + rename prevents corruption)."""
    with _state_lock:
        try:
            fd, tmp_path = tempfile.mkstemp(dir=STATE_FILE.parent, suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(state, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, STATE_FILE)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)

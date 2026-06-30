"""
Activity Log — a running feed of everything the bot does.

Writes timestamped entries to activity_log.jsonl (one JSON object per line).
Also sends muted Telegram notifications for important events.

Usage from anywhere in the bot:
    from activity_log import log_event, log_llm_call, log_scrape, log_system

    log_event("photo_processed", {"ocr_chars": 1234, "has_homework": True})
    log_llm_call("openrouter/owl-alpha", "photo-extract", 1500, 2.3)
    log_scrape("canvas", 5, "new assignments")
    log_system("mc_server", "started", {"ram_mb": 1500})

Events are also mirrored to Telegram as muted (silent) notifications
for important events (errors, scrapes, LLM calls, system changes).
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, "activity_log.jsonl")
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB max, then rotate
MAX_ENTRIES = 5000  # keep last 5000 entries after rotation

# Thread-safe write lock
_write_lock = threading.Lock()

# Telegram notification config
_TELEGRAM_TOKEN = None
_TELEGRAM_CHAT_ID = None


def _init_telegram():
    """Lazily load Telegram credentials."""
    global _TELEGRAM_TOKEN, _TELEGRAM_CHAT_ID
    if _TELEGRAM_TOKEN is not None:
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        _TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        _TELEGRAM_CHAT_ID = os.getenv("SANEL_CHAT_ID", "8534649457")
    except Exception:
        _TELEGRAM_TOKEN = ""


# Event categories that should trigger a muted Telegram notification
_NOTIFY_CATEGORIES = {
    "error", "llm_call", "scrape", "system", "nightly",
    "verification", "digest", "alert",
}

# Short label map for Telegram
_CATEGORY_ICONS = {
    "message": "\U0001f4ac",
    "photo": "\U0001f4f7",
    "voice": "\U0001f3a4",
    "llm_call": "\U0001f9e0",
    "scrape": "\U0001f4e5",
    "system": "\u2699\ufe0f",
    "nightly": "\U0001f319",
    "error": "\u274c",
    "digest": "\U0001f4f0",
    "verification": "\u2705",
    "alert": "\u26a0\ufe0f",
    "embed": "\U0001f9e0",
    "mc_server": "\u26cf\ufe0f",
    "guide_built": "\U0001f4da",
}


def _rotate_if_needed():
    """Trim the log file if it exceeds MAX_LOG_SIZE."""
    if not os.path.exists(LOG_PATH):
        return
    try:
        if os.path.getsize(LOG_PATH) < MAX_LOG_SIZE:
            return
        # Read all lines, keep last MAX_ENTRIES
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > MAX_ENTRIES:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                for line in lines[-MAX_ENTRIES:]:
                    f.write(line)
    except Exception:
        pass


def _send_telegram_notification(text: str):
    """Send a muted (silent) Telegram message."""
    _init_telegram()
    if not _TELEGRAM_TOKEN or not _TELEGRAM_CHAT_ID:
        return
    try:
        import httpx
        httpx.post(
            f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": _TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_notification": True,  # MUTED!
            },
            timeout=5.0,
        )
    except Exception:
        pass  # notifications are best-effort


def log_event(category: str, details: dict = None, notify: bool = None):
    """Log an activity event.

    Args:
        category: What happened (e.g. "message", "photo", "llm_call", "scrape", "error")
        details: Optional dict with event-specific data
        notify: Force notify (True) or suppress (False). Default: auto based on category.
    """
    entry = {
        "ts": time.time(),
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "cat": category,
        "details": details or {},
    }

    with _write_lock:
        _rotate_if_needed()
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # Telegram notification
    should_notify = notify if notify is not None else (category in _NOTIFY_CATEGORIES)
    if should_notify:
        icon = _CATEGORY_ICONS.get(category, "\U0001f4e5")
        # Build short summary
        summary = _format_event_short(icon, entry)
        _send_telegram_notification(summary)


def _format_event_short(icon: str, entry: dict) -> str:
    """Format an event for a compact Telegram notification."""
    d = entry.get("details", {})
    cat = entry.get("cat", "?")
    t = entry.get("time", "?")

    # Category-specific formatting
    if cat == "llm_call":
        model = d.get("model", "?")
        task = d.get("task", "")
        dur = d.get("duration_s", "?")
        cost = d.get("cost_usd", 0)
        return f"{icon} `{t}` `{model}` {task} ({dur}s, ${cost:.4f})"

    if cat == "scrape":
        source = d.get("source", "?")
        count = d.get("count", "?")
        note = d.get("note", "")
        return f"{icon} `{t}` Scraped {source}: {count} {note}".strip()

    if cat == "system":
        subsystem = d.get("subsystem", "?")
        action = d.get("action", "?")
        return f"{icon} `{t}` {subsystem}: {action}"

    if cat == "error":
        msg = d.get("message", "unknown error")[:80]
        source = d.get("source", "")
        return f"{icon} `{t}` {source}: {msg}" if source else f"{icon} `{t}` {msg}"

    if cat == "nightly":
        phase = d.get("phase", "?")
        status = d.get("status", "?")
        return f"{icon} `{t}` Nightly: {phase} {status}"

    if cat == "digest":
        sources = d.get("sources", "?")
        action = d.get("action", "sent")
        return f"{icon} `{t}` Digest {action} ({sources} sources)"

    # Generic
    detail_str = ""
    if d:
        detail_str = " " + " ".join(f"{k}={v}" for k, v in list(d.items())[:3])
    return f"{icon} `{t}` {cat}{detail_str}"


def log_llm_call(model: str, task: str, duration_s: float, cost_usd: float = 0,
                 tokens_in: int = 0, tokens_out: int = 0, is_local: bool = False):
    """Convenience: log an LLM call."""
    log_event("llm_call", {
        "model": model,
        "task": task,
        "duration_s": round(duration_s, 1),
        "cost_usd": round(cost_usd, 6),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "local": is_local,
    })


def log_scrape(source: str, count: int, note: str = ""):
    """Convenience: log a scrape event."""
    log_event("scrape", {"source": source, "count": count, "note": note})


def log_system(subsystem: str, action: str, details: dict = None):
    """Convenience: log a system event (MC server start/stop, etc)."""
    d = {"subsystem": subsystem, "action": action}
    if details:
        d.update(details)
    log_event("system", d)


def log_nightly(phase: str, status: str, details: dict = None):
    """Convenience: log a nightly pipeline event."""
    d = {"phase": phase, "status": status}
    if details:
        d.update(details)
    log_event("nightly", d, notify=True)


def get_recent_events(n: int = 30, category: str = None) -> list[dict]:
    """Read the last N events from the activity log, optionally filtered by category."""
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []

    events = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if category and entry.get("cat") != category:
                continue
            events.append(entry)
            if len(events) >= n:
                break
        except Exception:
            continue

    return list(reversed(events))  # newest last (chronological order)


def format_events(events: list[dict]) -> str:
    """Format events for display in Telegram."""
    if not events:
        return "No events logged yet."

    lines = []
    for e in events:
        cat = e.get("cat", "?")
        icon = _CATEGORY_ICONS.get(cat, "\U0001f4e5")
        t = e.get("time", "?")
        d = e.get("details", {})

        if cat == "llm_call":
            model = d.get("model", "?")
            task = d.get("task", "")
            dur = d.get("duration_s", "?")
            local = "LOCAL" if d.get("local") else "cloud"
            lines.append(f"`{t}` {icon} `{model}` {task} ({dur}s, {local})")
        elif cat == "scrape":
            source = d.get("source", "?")
            count = d.get("count", "?")
            note = d.get("note", "")
            lines.append(f"`{t}` {icon} {source}: {count} {note}".strip())
        elif cat == "system":
            subsystem = d.get("subsystem", "?")
            action = d.get("action", "?")
            lines.append(f"`{t}` {icon} {subsystem}: {action}")
        elif cat == "error":
            msg = d.get("message", "?")[:60]
            source = d.get("source", "")
            lines.append(f"`{t}` {icon} {source}: {msg}" if source else f"`{t}` {icon} {msg}")
        elif cat == "nightly":
            phase = d.get("phase", "?")
            status = d.get("status", "?")
            lines.append(f"`{t}` {icon} {phase}: {status}")
        elif cat == "message":
            msg = d.get("preview", "?")[:50]
            routed = d.get("routed_to", "?")
            lines.append(f"`{t}` {icon} \"{msg}\" -> {routed}")
        elif cat == "photo":
            has_q = d.get("has_question", False)
            chars = d.get("ocr_chars", 0)
            lines.append(f"`{t}` {icon} photo (OCR: {chars} chars, question: {has_q})")
        elif cat == "digest":
            action = d.get("action", "sent")
            sources = d.get("sources", "?")
            lines.append(f"`{t}` {icon} digest {action} ({sources} sources)")
        elif cat == "embed":
            action = d.get("action", "?")
            chunks = d.get("chunks", "?")
            lines.append(f"`{t}` {icon} embed: {action} ({chunks} chunks)")
        else:
            detail_str = " ".join(f"{k}={v}" for k, v in list(d.items())[:3]) if d else ""
            lines.append(f"`{t}` {icon} {cat} {detail_str}".strip())

    return "\n".join(lines)

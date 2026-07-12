import logging
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        from config import SANEL_CHAT_ID
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = SANEL_CHAT_ID

    _TELEGRAM_ERROR_FRAGMENTS = (
        "Can't parse entities",
        "can't find end of the entity",
        "Can't find end of the entity",
        "can't parse entities",
        "bad request: can't parse",
        "Bad Request: can't parse",
        "entity starting at byte offset",
        "Telegram send failed",
    )

    def _is_telegram_feedback_loop(self, record: logging.LogRecord) -> bool:
        """Check if this log record is itself a Telegram API error that would
        trigger a re-send loop if we forwarded it to Telegram."""
        msg = record.getMessage()
        for frag in self._TELEGRAM_ERROR_FRAGMENTS:
            if frag in msg:
                return True
        return False

    def emit(self, record):
        if not self.token or not self.chat_id:
            return

        # BREAK THE FEEDBACK LOOP: never re-send Telegram API errors back
        # to Telegram — that's how "Can't parse entities" gets forwarded
        # as a new `⚙️ Watchdog Ollama error: Can't parse entities...` message.
        if self._is_telegram_feedback_loop(record):
            return

        # Ignore noisy internal library logs
        if record.name.startswith("urllib3") or record.name.startswith("httpx") or record.name.startswith("telegram") or record.name.startswith("apscheduler"):
            return

        from utils import scrub_pii
        log_entry = scrub_pii(self.format(record))

        # Also scrub markdown-breaking chars from the log entry before wrapping
        from utils import sanitize_markdown
        safe_entry = sanitize_markdown(log_entry)

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"⚙️ `{safe_entry}`",
            "parse_mode": "Markdown",
            "disable_notification": True
        }
        try:
            requests.post(url, json=payload, timeout=2)
        except Exception:
            pass

def setup_telegram_logging():
    logger = logging.getLogger()
    
    # Check if we already have a TelegramHandler to avoid duplicates
    if any(isinstance(h, TelegramHandler) for h in logger.handlers):
        return
        
    handler = TelegramHandler()
    handler.setLevel(logging.WARNING)  # Send WARNING+ to Telegram as muted notifications
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

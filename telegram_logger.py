import logging
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = "8534649457" # Discovered from history files

    def emit(self, record):
        if not self.token or not self.chat_id:
            return
        log_entry = self.format(record)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id, 
            "text": f"⚙️ `{log_entry}`", 
            "parse_mode": "Markdown",
            "disable_notification": True
        }
        try:
            requests.post(url, json=payload, timeout=2)
        except:
            pass

def setup_telegram_logging():
    logger = logging.getLogger()
    
    # Check if we already have a TelegramHandler to avoid duplicates
    if any(isinstance(h, TelegramHandler) for h in logger.handlers):
        return
        
    handler = TelegramHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

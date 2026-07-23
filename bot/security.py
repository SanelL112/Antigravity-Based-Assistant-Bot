import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os

# Ensure config is available
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SANEL_CHAT_ID

logger = logging.getLogger(__name__)

def require_auth(func):
    """
    Decorator to ensure that only the authorized user (SANEL_CHAT_ID)
    can execute the decorated command handler.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # A command without a Telegram update has no identity to authorize.
        # Never treat this as an internal/trusted call: handlers are an external
        # boundary and must fail closed when Telegram context is unavailable.
        if not update:
            logger.warning("Unauthorized handler invocation without an update")
            return None

        # Get chat ID safely
        chat_id = None
        if update.effective_chat:
            chat_id = update.effective_chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat_id
            
        if chat_id is None or str(chat_id) != str(SANEL_CHAT_ID):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            if update.message:
                await update.message.reply_text("⛔ Unauthorized. You do not have permission to use this bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized", show_alert=True)
            return None
            
        return await func(update, context, *args, **kwargs)
        
    return wrapper

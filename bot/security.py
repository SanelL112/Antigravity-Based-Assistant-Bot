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
        # Allow missing update (e.g. from tests or internal calls)
        if not update:
            return await func(update, context, *args, **kwargs)
            
        # Get chat ID safely
        chat_id = None
        if update.effective_chat:
            chat_id = update.effective_chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat_id
            
        if chat_id and str(chat_id) != str(SANEL_CHAT_ID):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            if update.message:
                await update.message.reply_text("⛔ Unauthorized. You do not have permission to use this bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized", show_alert=True)
            return None
            
        return await func(update, context, *args, **kwargs)
        
    return wrapper

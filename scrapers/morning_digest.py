import os
import requests
import asyncio
from telegram import Bot
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = "38309c49-e758-8004-8005-c5440093e2cb"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SANEL_CHAT_ID = 8534649457

def get_pending_tasks():
    if not NOTION_API_KEY: return []
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "filter": {
            "property": "Status",
            "status": {
                "equals": "Not started"
            }
        }
    }
    try:
        res = requests.post(query_url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        results = res.json().get("results", [])
        tasks = []
        for r in results:
            title_props = r.get("properties", {}).get("Task name", {}).get("title", [])
            title = title_props[0].get("text", {}).get("content", "Unknown") if title_props else "Unknown"
            tasks.append(title)
        return tasks
    except Exception as e:
        logger.error(f"Failed to fetch pending tasks: {e}")
        return []

async def send_morning_digest():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    context_file = os.path.join(base_dir, "bot_context.txt")
    
    bot_context = ""
    if os.path.exists(context_file):
        with open(context_file, "r", encoding="utf-8") as f:
            bot_context = f.read().strip()
            
    tasks = get_pending_tasks()
    
    msg = "☀️ **GOOD MORNING! Here is your Daily Digest.**\n\n"
    
    if bot_context:
        msg += f"🧠 **Current Brain Context:**\n{bot_context}\n\n"
        
    if tasks:
        msg += "📋 **Pending Notion Tasks:**\n"
        for t in tasks:
            msg += f"- {t}\n"
        msg += "\n_Reply to me with updates on your progress for any of these tasks!_"
    else:
        msg += "📋 **Pending Tasks:** You have no pending tasks in Notion! Great job."
        
    try:
        await bot.send_message(chat_id=SANEL_CHAT_ID, text=msg, parse_mode="Markdown")
        logger.info("Morning digest sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send digest: {e}")

if __name__ == "__main__":
    asyncio.run(send_morning_digest())

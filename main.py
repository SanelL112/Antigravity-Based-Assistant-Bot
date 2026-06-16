import os
import json
import logging
import asyncio
import subprocess
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ── Config ─────────────────────────────────────────────────────────────────────
load_dotenv()
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CONVERSATION_ID     = os.getenv("CONVERSATION_ID")
AGENTAPI_BIN        = os.getenv("AGENTAPI_BIN", "/home/sanellathiya/.gemini/antigravity-cli/bin/agentapi")
TRANSCRIPT_PATH     = os.getenv(
    "TRANSCRIPT_PATH",
    f"/home/sanellathiya/.gemini/antigravity-cli/brain/{CONVERSATION_ID}/.system_generated/logs/transcript.jsonl"
)
POLL_INTERVAL       = 2    # seconds between transcript polls
RESPONSE_TIMEOUT    = 120  # seconds to wait for a reply

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ── Transcript helpers ─────────────────────────────────────────────────────────

def get_last_step_index() -> int:
    """Return the highest step_index currently in the transcript."""
    last = -1
    try:
        with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    idx = obj.get("step_index", -1)
                    if idx > last:
                        last = idx
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return last


def get_new_responses(after_step: int) -> list[str]:
    """
    Return a list of completed PLANNER_RESPONSE content strings
    that appear after `after_step`.
    """
    responses = []
    try:
        with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    obj.get("step_index", -1) > after_step
                    and obj.get("source") == "MODEL"
                    and obj.get("type") == "PLANNER_RESPONSE"
                    and obj.get("status") == "DONE"
                ):
                    content = obj.get("content", "").strip()
                    if content:
                        responses.append(content)
    except FileNotFoundError:
        pass
    return responses


# ── Bridge logic ───────────────────────────────────────────────────────────────

async def send_to_antigravity_and_wait(user_message: str, chat_id: int = 0) -> str:
    """Uses agy --print for a direct response. Works standalone on Debian."""
    system = (
        "You are a smart personal assistant for Sanel Lathiya. "
        "Answer helpfully and concisely."
    )
    full_prompt = system + chr(10) + chr(10) + 'User: ' + user_message
    model = user_models.get(chat_id, "flash")
    logger.info(f"agy --continue --print model={model}: {user_message[:60]}")
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [AGENTAPI_BIN, "--continue", "--print", full_prompt],
                    capture_output=True, text=True, timeout=RESPONSE_TIMEOUT
                )
            ),
            timeout=RESPONSE_TIMEOUT + 5
        )
        out = result.stdout.strip()
        if not out:
            logger.error(f"Empty agy output. stderr: {result.stderr[:300]}")
            return "⚠️ No response from assistant. Please try again."
        return out
    except asyncio.TimeoutError:
        return "⏳ Assistant is taking too long. Try again shortly."
    except Exception as e:
        logger.error(f"agy error: {e}")
        return "⚠️ Failed to reach assistant."


# ── Background Automation ──────────────────────────────────────────────────────

import hashlib
import sys
STATE_FILE = "state.json"

def get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"seen_tasks": [], "seen_alerts": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

async def check_updates(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    state = load_state()
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_upcoming_assignments
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments
    from ai_processor import process_all_sources
    from notion_client import add_task_to_notion
    
    logger.info("Background job: Scraping sources...")
    canvas = get_upcoming_assignments()
    classroom = get_classroom_assignments()
    gmail = get_unread_emails()
    groupme = get_latest_messages("102851186")
    
    logger.info("Background job: Processing with AI...")
    ai_result = process_all_sources(canvas, classroom, gmail, groupme)
    
    # 1. Notion Tasks
    for task in ai_result.get("tasks", []):
        thash = get_hash(task.get("title", ""))
        if thash not in state.setdefault("seen_tasks", []):
            add_task_to_notion(
                title=task.get("title"),
                source=task.get("source"),
                due_date=task.get("due_date"),
                url=task.get("url")
            )
            state["seen_tasks"].append(thash)
            logger.info(f"Pushed task to Notion: {task.get('title')}")
            
    # 2. Telegram Alerts
    for alert in ai_result.get("alerts", []):
        ahash = get_hash(alert.get("summary", ""))
        if ahash not in state.setdefault("seen_alerts", []):
            text = f"🔔 **New Alert from {alert.get('source')}**\nFrom: {alert.get('from', 'Unknown')}\n\n{alert.get('summary')}"
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            state["seen_alerts"].append(ahash)
            
    state["seen_tasks"] = state.get("seen_tasks", [])[-50:]
    state["seen_alerts"] = state.get("seen_alerts", [])[-50:]
    save_state(state)
    logger.info("Background job: Complete.")


# ── Telegram handlers ──────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Enable background polling every 5 minutes
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    context.job_queue.run_repeating(check_updates, interval=300, first=5, chat_id=chat_id, name=str(chat_id))
    
    await update.message.reply_text(
        "👋 Hey! I'm your personal Antigravity assistant.\n\n"
        "🟢 **Background Automation is ACTIVE.** I will now silently check your Canvas and GroupMe every 5 minutes and text you if there are new updates.\n\n"
        "You can also message me anytime to run a specific command."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id   = update.effective_chat.id

    # Send a "thinking" indicator
    thinking_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Thinking..."
    )

    reply = await send_to_antigravity_and_wait(user_text, chat_id)

    # Delete the thinking message
    await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)

    # Telegram messages max out at 4096 chars; split if needed
    max_len = 4096
    for i in range(0, len(reply), max_len):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reply[i:i+max_len],
                parse_mode="Markdown"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reply[i:i+max_len]
            )



async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    valid = ["flash", "pro", "flash_lite"]
    if not args or args[0] not in valid:
        current = user_models.get(chat_id, "flash")
        await update.message.reply_text(
            f"Current model: *{current}*\n\nUsage: `/model flash` | `/model pro` | `/model flash_lite`",
            parse_mode="Markdown"
        )
        return
    user_models[chat_id] = args[0]
    await update.message.reply_text(f"Model switched to *{args[0]}* ✅", parse_mode="Markdown")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("Please set TELEGRAM_BOT_TOKEN in .env")
        exit(1)
    if not CONVERSATION_ID:
        print("Please set CONVERSATION_ID in .env")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Antigravity Telegram bridge is running...")
    app.run_polling()

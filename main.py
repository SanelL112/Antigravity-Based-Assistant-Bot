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
user_models = {}
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


# ── Topic detection ───────────────────────────────────────────────────────────

TOPIC_KEYWORDS = {
    "server": [
        "server", "bot", "install", "restart", "log", "service", "systemd", "process",
        "bash", "command", "code", "git", "python", "script", "file", "disk", "cpu",
        "memory", "ram", "port", "ssh", "deploy", "update", "package", "apt", "run",
        "debug", "error", "crash", "status", "config", "environment", "docker"
    ],
    "school": [
        "canvas", "assignment", "homework", "class", "course", "school", "grade",
        "notion", "task", "due", "quiz", "test", "exam", "teacher", "student",
        "classroom", "lecture", "study", "project", "submit", "deadline", "ap",
        "groupme", "club", "tsa", "skills", "robotics", "hosa", "biotech"
    ],
}

async def detect_topic(message: str, chat_id: int) -> str:
    """Detect conversation topic using local Ollama model. Returns an existing topic or invents a new one."""
    import glob
    import re
    history_dir = os.path.dirname(os.path.abspath(__file__))
    existing_files = glob.glob(os.path.join(history_dir, f"chat_history_{chat_id}_*.txt"))
    
    existing_topics = []
    for f in existing_files:
        basename = os.path.basename(f)
        m = re.search(f"chat_history_{chat_id}_(.+)\\.txt", basename)
        if m:
            existing_topics.append(m.group(1))
            
    topics_list_str = ", ".join(existing_topics) if existing_topics else "None"

    prompt = (
        "You are a topic classifier and router. Your job is to organize a user's messages into distinct conversation files.\n"
        f"The existing topics are: [{topics_list_str}].\n"
        "If the following message perfectly matches one of the existing topics, reply with that exact topic name.\n"
        "If it is a completely new subject, invent a short, 1-2 word topic name for it (e.g., 'math_homework', 'python_bot', 'fitness').\n"
        "Reply with ONLY the topic name in lowercase, using underscores instead of spaces. Do not write anything else.\n\n"
        f"Message: {message}"
    )
    
    topic = "general"
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                },
                timeout=10.0
            )
        if response.status_code == 200:
            result = response.json().get("response", "").strip().lower()
            # Clean up output to be a valid filename string
            result = re.sub(r'[^a-z0-9_]', '', result.replace(' ', '_'))
            if result:
                topic = result
    except Exception as e:
        logger.error(f"Ollama topic detection failed: {e}")
    
    return topic


# ── Bridge logic ───────────────────────────────────────────────────────────────

async def send_to_antigravity_and_wait(user_message: str, chat_id: int = 0) -> str:
    """Uses agy --print for a direct response. Works standalone on Debian."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_digest.txt"), "r") as f:
            digest_context = f.read()
    except Exception:
        digest_context = "No recent data available."

    # Detect topic and load the matching history file
    topic = await detect_topic(user_message, chat_id)
    history_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(history_dir, f"chat_history_{chat_id}_{topic}.txt")
    logger.info(f"Topic detected: {topic} -> {os.path.basename(history_file)}")

    system = (
        f"You are a powerful personal assistant AI for Sanel Lathiya running on his personal Debian server. "
        f"You have FULL ROOT ACCESS to the server and can execute any shell command automatically.\n\n"
        f"CURRENT CONVERSATION TOPIC: {topic}\n"
        f"You are in a focused conversation about this topic. Stay on topic unless Sanel switches subjects.\n\n"
        f"CRITICAL INSTRUCTION — COMMAND EXECUTION:\n"
        f"When Sanel asks you to DO something on the server (install software, restart services, check logs, "
        f"edit files, run scripts, manage processes, etc.), you MUST execute it yourself immediately. "
        f"Do NOT tell him to run /bash himself. Instead, wrap the shell command in <BASH> tags like this:\n"
        f"<BASH>your command here</BASH>\n"
        f"The system will automatically run that command as root and show him the output. "
        f"You can chain multiple commands. Always include <BASH> tags when action is needed.\n\n"
        f"OTHER CAPABILITIES:\n"
        f"- Every 4 hours: auto-digest from Canvas, Classroom, Gmail, GroupMe\n"
        f"- Notion: assignments auto-pushed to Tasks Tracker\n"
        f"- /summary: manual digest trigger | /bash <cmd>: run commands directly\n\n"
        f"Here is the latest data digest:\n\n{digest_context}\n\n"
        f"Be direct and take action immediately when asked. Never ask for permission."
    )

    try:
        with open(history_file, "r") as f:
            chat_history = f.read()
    except Exception:
        chat_history = ""

    # Cap history to last 4000 chars per topic
    if len(chat_history) > 4000:
        chat_history = "[earlier messages trimmed]\n" + chat_history[-4000:]

    full_prompt = (system + "\n\n"
                   f"--- {topic.upper()} CONVERSATION HISTORY ---\n"
                   + chat_history +
                   f"\n--- END HISTORY ---\n\nUser: " + user_message)
    
    model = user_models.get(chat_id, "flash")
    logger.info(f"agy --print model={model}: {user_message[:60]}")
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [AGENTAPI_BIN, "--model", model, "--print", full_prompt],
                    capture_output=True, text=True, timeout=RESPONSE_TIMEOUT
                )
            ),
            timeout=RESPONSE_TIMEOUT + 5
        )
        out = result.stdout.strip()
        if not out:
            logger.error(f"Empty agy output. stderr: {result.stderr[:300]}")
            return "⚠️ No response from assistant. Please try again."

        # Auto-execute any <BASH>...</BASH> blocks in the response
        import re as _re
        def _run_bash(cmd):
            try:
                r = subprocess.run(
                    f"echo 'Forgot@2023' | sudo -S bash -c {repr(cmd.strip())}",
                    shell=True, capture_output=True, text=True, timeout=60
                )
                result_text = (r.stdout + r.stderr).strip()
                result_text = "\n".join(l for l in result_text.splitlines() if not l.startswith("[sudo]"))
                return result_text[:2000] if result_text else "(no output)"
            except Exception as ex:
                return f"Error: {ex}"

        def _replace_bash(m):
            cmd = m.group(1).strip()
            logger.info(f"Auto-executing: {cmd[:80]}")
            output = _run_bash(cmd)
            return f"\n💻 `{cmd}`\n```\n{output}\n```"

        out = _re.sub(r'<BASH>(.*?)</BASH>', _replace_bash, out, flags=_re.DOTALL)

        # Append turn to custom history file
        with open(history_file, "a") as f:
            f.write(f"User: {user_message}\nModel: {out}\n\n")
            
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

async def watchdog_check(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 30 mins to check for urgent anomalies using tiny local model Qwen2 0.5B."""
    chat_id = context.job.chat_id
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements
    
    logger.info("Watchdog: Scraping sources...")
    try:
        canvas = get_all_canvas_data()
        classroom = get_classroom_assignments()
        classroom_ann = get_classroom_announcements()
        gmail = get_unread_emails()
        groupme = get_latest_messages("102851186")
    except Exception as e:
        logger.error(f"Watchdog scrape error: {e}")
        return

    raw_data = f"CANVAS:\n{canvas[:800]}\n\nCLASSROOM:\n{classroom[:800]}\n\nCLASSROOM ANNOUNCEMENTS:\n{classroom_ann[:800]}\n\nGMAIL:\n{gmail[:800]}\n\nGROUPME:\n{groupme[:800]}"
    
    prompt = (
        "You are an urgent alert watchdog. Read the following recent school and email notifications.\n"
        "Look ONLY for critical anomalies or urgent updates (e.g., a sudden deadline extension, a direct message from a teacher, or an emergency alert).\n"
        "If you find something genuinely urgent, write a short 1-sentence warning about it.\n"
        "If there is nothing urgent, you MUST reply with exactly the word: NO_ALERT\n\n"
        f"DATA:\n{raw_data}"
    )

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2:0.5b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                },
                timeout=120.0
            )
        if response.status_code == 200:
            result = response.json().get("response", "").strip()
            if result and "NO_ALERT" not in result and len(result) > 10:
                logger.info(f"Watchdog triggered: {result}")
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"🚨 **WATCHDOG ALERT** 🚨\n\n{result}",
                    parse_mode="Markdown"
                )
            else:
                logger.info("Watchdog check clear (no alerts).")
    except Exception as e:
        logger.error(f"Watchdog Ollama error: {e}")

async def check_updates(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    state = load_state()
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements
    from ai_processor import process_all_sources
    from notion_client import add_task_to_notion
    
    logger.info("Background job: Scraping sources...")
    canvas = get_all_canvas_data()
    classroom = get_classroom_assignments()
    classroom_ann = get_classroom_announcements()
    gmail = get_unread_emails()
    groupme = get_latest_messages("102851186")
    
    logger.info("Background job: Processing with AI...")
    ai_result = process_all_sources(canvas, classroom, gmail, groupme, classroom_ann)
    
    # 1. Notion Tasks
    for task in ai_result.get("tasks", []):
        thash = get_hash(task.get("id", task.get("title", "")))
        if thash not in state.setdefault("seen_tasks", []):
            add_task_to_notion(
                title=task.get("title"),
                source=task.get("source"),
                due_date=task.get("due_date"),
                url=task.get("url"),
                priority=task.get("priority", "medium"),
                status="Not started",
                start_value=task.get("start_value", 0),
                end_value=task.get("end_value", 100),
            )
            state["seen_tasks"].append(thash)
            logger.info(f"Pushed task to Notion: {task.get('title')}")
            
    # 2. Telegram Digest
    digest = ai_result.get("digest", "")
    if digest and digest != "Nothing to report right now!":
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_digest.txt"), "w") as f:
                f.write(digest)
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📊 **Periodic Digest**\n\n{digest}", parse_mode="Markdown")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"📊 **Periodic Digest**\n\n{digest}")
            
    state["seen_tasks"] = state.get("seen_tasks", [])[-50:]
    save_state(state)
    logger.info("Background job: Complete.")


# ── Telegram handlers ──────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Enable background polling every 5 minutes
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    context.job_queue.run_repeating(check_updates, interval=14400, first=5, chat_id=chat_id, name=str(chat_id))
    
    await update.message.reply_text(
        "👋 Hey! I'm your personal Antigravity assistant.\n\n"
        "🟢 **Background Automation is ACTIVE.** I will now check your Canvas, Gmail, Classroom, and GroupMe and send you a comprehensive digest every 4 hours.\n\n"
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


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Generating your summary digest... This might take a minute.")
    
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments
    from ai_processor import process_all_sources
    
    canvas = get_all_canvas_data()
    classroom = get_classroom_assignments()
    gmail = get_unread_emails()
    groupme = get_latest_messages("102851186")
    
    ai_result = process_all_sources(canvas, classroom, gmail, groupme)
    digest = ai_result.get("digest", "Nothing to report right now!")
    if digest and digest != "Nothing to report right now!":
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_digest.txt"), "w") as f:
                f.write(digest)
        except Exception:
            pass
            
    await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
    try:
        await context.bot.send_message(chat_id=chat_id, text=f"📊 **On-Demand Digest**\n\n{digest}", parse_mode="Markdown")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=f"📊 **On-Demand Digest**\n\n{digest}")


async def bash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != 8534649457:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized.")
        return

    cmd = " ".join(context.args)
    if not cmd:
        await context.bot.send_message(chat_id=chat_id, text="Usage: `/bash <command>`", parse_mode="Markdown")
        return

    msg = await context.bot.send_message(chat_id=chat_id, text=f"💻 Running: `{cmd}`...", parse_mode="Markdown")
    try:
        # Run with full root access via sudo
        full_cmd = "echo 'Forgot@2023' | sudo -S bash -c " + repr(cmd)
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        # Strip the sudo password prompt line
        output = "\n".join(line for line in output.splitlines() if not line.startswith("[sudo]"))
        if not output.strip():
            output = "(No output)"
        if len(output) > 3800:
            output = output[:3800] + "\n... (truncated)"
        reply = "💻 **`" + cmd + "`**\n\n```\n" + output + "\n```"
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id, text=reply, parse_mode="Markdown"
            )
        except Exception:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id, text=reply
            )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text="❌ Error: " + str(e)
        )

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("Please set TELEGRAM_BOT_TOKEN in .env")
        exit(1)
    if not CONVERSATION_ID:
        print("Please set CONVERSATION_ID in .env")
        exit(1)


    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Auto-start the background 4-hour digest task for the user on boot
    SANEL_CHAT_ID = 8534649457
    job_queue = app.job_queue
    job_queue.run_repeating(check_updates, interval=14400, first=60, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_digest")
    
    # Auto-start the 30-minute watchdog
    job_queue.run_repeating(watchdog_check, interval=1800, first=15, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_watchdog")
    
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("bash", bash_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Antigravity Telegram bridge is running...")
    app.run_polling()

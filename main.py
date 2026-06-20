import os
import json
import logging
import asyncio
import subprocess
import datetime
import pytz
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ── Config ─────────────────────────────────────────────────────────────────────
load_dotenv()
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CONVERSATION_ID     = os.getenv("CONVERSATION_ID")
AGENTAPI_BIN        = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")
SUDO_PASSWORD       = os.getenv("SUDO_PASSWORD", "")
TRANSCRIPT_PATH     = os.getenv(
    "TRANSCRIPT_PATH",
    f"/home/sanellathiya/.gemini/antigravity-cli/brain/{CONVERSATION_ID}/.system_generated/logs/transcript.jsonl"
)
user_models = {}
POLL_INTERVAL       = 2    # seconds between transcript polls
RESPONSE_TIMEOUT    = 300  # seconds to wait for a reply

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
    
    try:
        import subprocess
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", prompt],
                    capture_output=True, text=True, timeout=15
                )
            ),
            timeout=20
        )
        topic = result.stdout.strip().lower()
        topic = re.sub(r'[^a-z0-9_]', '', topic.replace(' ', '_'))
        if len(topic) > 30:
            logger.warning(f"Topic name too long from flash model, falling back to 'general': {topic}")
            return "general"
        return topic if topic else "general"
    except Exception as e:
        logger.error(f"Topic detection failed: {e}")
        return "general"


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
        f"You are operating in a pure text-generation mode. DO NOT use any of your built-in Antigravity tools (like run_command or write_file). "
        f"When Sanel asks you to DO something on the server, you MUST instead wrap the shell command in <BASH> tags like this:\n"
        f"<BASH>your command here</BASH>\n"
        f"The system's python wrapper will automatically parse these tags and run that command as root, then show you the output in the next turn. "
        f"You can chain multiple commands. Always include <BASH> tags when action is needed.\n\n"
        f"OTHER CAPABILITIES:\n"
        f"- Every 4 hours: auto-digest from Canvas, Classroom, Gmail, GroupMe\n"
        f"- Notion: assignments auto-pushed to Tasks Tracker\n"
        f"- Natural Language Notion Pushes: When the background job alerts Sanel about a NEW task and asks him for priority/status, you MUST push it to Notion using the add_task_to_notion python script when he replies! Example:\n"
        f"<BASH>python3 -c 'from notion_client import add_task_to_notion; add_task_to_notion(title=\"Math Homework\", priority=\"high\", status=\"Not started\", start_value=0, end_value=100)'</BASH>\n"
        f"- DYNAMIC LEARNING: If Sanel is answering a question about whether a certain type of message, email, or topic is important to track or ignore, you MUST save this rule to the local memory so the local filter AI can use it in the future. To do this, use a bash command:\n"
        f"<BASH>echo 'Ignore all emails from XYZ' >> /home/sanel/personal-assistant-bot/learning_rules.txt</BASH>\n"
        f"- STUDY COMPANION: If Sanel asks you to build a study guide, find a YouTube video for a topic, or research something to study, you MUST use the mega study builder script via bash:\n"
        f"<BASH>python3 -c 'from mega_study_builder import generate_mega_guide; print(generate_mega_guide(\"Topic Name Here\"))'</BASH>\n"
        f"- CALENDAR SCHEDULING: If Sanel asks you to schedule a study session, block off time, or add something to his calendar, you MUST use the calendar manager via bash. Calculate the start time in ISO format based on his request and current time:\n"
        f"<BASH>python3 -c 'from scrapers.calendar_manager import add_study_session; print(add_study_session(\"Task Name\", \"2026-06-20T14:00:00\", 120))'</BASH>\n"
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
    
    out = ""
    if model.startswith("openrouter:"):
        or_model_name = model.split("openrouter:", 1)[1]
        logger.info(f"OpenRouter model={or_model_name}: {user_message[:60]}")
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                        "HTTP-Referer": "https://github.com/SanelL112/TaskBot",
                        "X-Title": "TaskBot"
                    },
                    json={
                        "model": or_model_name,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": f"--- {topic.upper()} CONVERSATION HISTORY ---\n{chat_history}\n--- END HISTORY ---\n\nUser: {user_message}"}
                        ]
                    },
                    timeout=180.0
                )
                if resp.status_code == 200:
                    out = resp.json()["choices"][0]["message"]["content"].strip()
                else:
                    out = f"⚠️ OpenRouter Error: {resp.status_code} {resp.text}"
        except Exception as e:
            out = f"⚠️ OpenRouter Exception: {e}"
    else:
        logger.info(f"agy --print model={model}: {user_message[:60]}")
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [AGENTAPI_BIN, "--model", model, "--dangerously-skip-permissions", "--print", full_prompt],
                        capture_output=True, text=True, timeout=RESPONSE_TIMEOUT, stdin=subprocess.DEVNULL
                    )
                ),
                timeout=RESPONSE_TIMEOUT + 5
            )
            out = result.stdout.strip()
            if not out:
                out = "⚠️ Assistant returned empty output. " + result.stderr[:200]
        except Exception as e:
            out = f"⚠️ Assistant timed out or failed: {e}"

    # Auto-execute any <BASH>...</BASH> blocks in the response
    import re as _re
    
    # Safety: block obviously destructive commands
    BLOCKED_PATTERNS = ['rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork bomb', '> /dev/sda', 'chmod -R 777 /', 'shutdown', 'reboot', 'init 0']
    
    def _run_bash(cmd):
        # Safety check
        for blocked in BLOCKED_PATTERNS:
            if blocked in cmd.lower():
                logger.warning(f"BLOCKED dangerous command: {cmd[:80]}")
                return f"⛔ BLOCKED: Command matched safety filter ({blocked})"
        try:
            sudo_pw = SUDO_PASSWORD or os.getenv('SUDO_PASSWORD', '')
            if sudo_pw:
                full_cmd = f"echo '{sudo_pw}' | sudo -S bash -c {repr(cmd.strip())}"
            else:
                full_cmd = f"bash -c {repr(cmd.strip())}"
            r = subprocess.run(
                full_cmd,
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

    # Append turn to custom history file (with rotation)
    with open(history_file, "a") as f:
        f.write(f"User: {user_message}\nModel: {out}\n\n")
    # Rotate if file exceeds 50KB to prevent unbounded growth
    try:
        if os.path.getsize(history_file) > 50000:
            with open(history_file, "r") as f:
                content = f.read()
            with open(history_file, "w") as f:
                f.write(content[-40000:])  # Keep last 40KB
            logger.info(f"Rotated history file: {os.path.basename(history_file)}")
    except Exception:
        pass
        
    return out



# ── Background Automation ──────────────────────────────────────────────────────

import hashlib
import sys
STATE_FILE = "state.json"

import pytz
import datetime
def is_sleep_window() -> bool:
    """Returns True if the current time is between 1 AM and 7 AM Eastern Time."""
    try:
        et_tz = pytz.timezone('US/Eastern')
        now_et = datetime.datetime.now(pytz.utc).astimezone(et_tz)
        if 1 <= now_et.hour < 7:
            return True
        return False
    except Exception:
        return False

def get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            if "pending_priorities" not in state:
                state["pending_priorities"] = {}
            return state
    return {"seen_tasks": [], "seen_alerts": [], "pending_priorities": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

async def watchdog_check(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 30 mins to check for urgent anomalies using tiny local model Qwen2 0.5B."""
    if is_sleep_window(): return
    chat_id = context.job.chat_id
    state = load_state()
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements
    
    logger.info("Watchdog: Scraping sources...")
    def _run_watchdog_scrape():
        return (
            get_all_canvas_data(),
            get_classroom_assignments(),
            get_classroom_announcements(),
            get_unread_emails(),
            get_latest_messages("102851186")
        )

    try:
        canvas, classroom, classroom_ann, gmail, groupme = await asyncio.to_thread(_run_watchdog_scrape)
    except Exception as e:
        logger.error(f"Watchdog scrape error: {e}")
        return

    raw_data = f"CANVAS:\n{canvas}\n\nCLASSROOM:\n{classroom}\n\nCLASSROOM ANNOUNCEMENTS:\n{classroom_ann}\n\nGMAIL:\n{gmail}\n\nGROUPME:\n{groupme}"
    
    import re
    import json
    
    # Match all attached files
    all_files = re.findall(r"📎\s+([^\(]+)\s*\((https://drive\.google\.com/file/d/([^/]+)/[^\)]+)\)", classroom)
    
    nightly_queue_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nightly_queue.json")
    try:
        with open(nightly_queue_path, "r") as f:
            nightly_queue = json.load(f)
    except Exception:
        nightly_queue = []
        
    queue_updated = False

    for title, full_link, file_id in all_files:
        thash = get_hash("file_" + file_id)
        if thash not in state.setdefault("seen_tasks", []):
            state["seen_tasks"].append(thash)
            save_state(state)
            
            title = title.strip()
            if "A_MWF" in title:
                # Auto-read handwritten notes
                await context.bot.send_message(chat_id=chat_id, text=f"📝 **Auto-Reading Notes**: I noticed `{title}`. Automatically extracting the handwriting in the background to learn what you did today...")
                
                # Run it in a background thread to not block the event loop
                import asyncio
                loop = asyncio.get_event_loop()
                def _extract():
                    import tempfile
                    from scrapers.google_scraper import download_drive_file
                    from scrapers.extract_notes import transcribe_handwritten_pdf
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        path = tmp.name
                    if download_drive_file(file_id, path):
                        transcript = transcribe_handwritten_pdf(path)
                        os.remove(path)
                        
                        if "Error:" not in transcript:
                            # Save to combined_summaries
                            notes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "combined_summaries.txt")
                            os.makedirs(os.path.dirname(notes_file), exist_ok=True)
                            with open(notes_file, "a") as f:
                                f.write(f"\n--- DAILY NOTES ({title}) ---\n{transcript}\n")
                            return True
                    return False
                    
                await asyncio.to_thread(_extract)
            else:
                # Add to nightly queue
                nightly_queue.append({"title": title, "file_id": file_id})
                queue_updated = True
                
    if queue_updated:
        with open(nightly_queue_path, "w") as f:
            json.dump(nightly_queue, f)
        await context.bot.send_message(chat_id=chat_id, text=f"🛏️ Queued {len(nightly_queue)} new practice materials for processing offline tonight.")
    
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
                    "model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                },
                timeout=45.0
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
    if is_sleep_window(): return
    chat_id = context.job.chat_id
    state = load_state()
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements, get_recent_google_docs
    from ai_processor import process_all_sources
    from notion_client import add_task_to_notion, update_notion_task
    
    logger.info("Background job: Scraping sources...")
    
    def _run_digest():
        c = get_all_canvas_data()
        cl = get_classroom_assignments()
        cla = get_classroom_announcements()
        gm = get_unread_emails()
        grp = get_latest_messages("102851186")
        gd = get_recent_google_docs()
        logger.info("Background job: Processing with AI...")
        return process_all_sources(c, cl, gm, grp, cla, gd)

    ai_result = await asyncio.to_thread(_run_digest)
    
    # 1. Notion Tasks
    new_tasks = []
    for task in ai_result.get("tasks", []):
        thash = get_hash(task.get("id", task.get("title", "")))
        if thash not in state.setdefault("seen_tasks", []):
            new_tasks.append(task)
            state["seen_tasks"].append(thash)
    save_state(state)
    
    if new_tasks:
        tasks_str = ""
        for i, task in enumerate(new_tasks, 1):
            tasks_str += f"{i}. {task.get('title')} (Source: {task.get('source')})\n"
        
        msg_text = f"🚨 **NEW TASKS DETECTED** 🚨\n\n{tasks_str}\nShould I add these to Notion? If yes, reply telling me their priority (high/medium/low) and progress. If I should ignore any of them, let me know so I can learn!"
        
        try:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=msg_text,
                parse_mode="Markdown"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=msg_text
            )
                
        # Append to Notion history so the LLM knows the Page ID
        history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chat_history_{chat_id}_notion.txt")
        with open(history_file, "a") as f:
            f.write(f"System Background Job: {msg_text}\n")
            
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
            
    # 3. Ask to Compile Mega Study Guides
    topics = ai_result.get("topics", [])
    if topics:
        topics_str = "\n".join([f"- {t}" for t in topics])
        msg = (
            f"🧠 **I detected you have upcoming assignments/tests for the following topics:**\n"
            f"{topics_str}\n\n"
            f"Would you like me to compile a Mega Study Guide for any of these? (Just reply 'Build a guide for...') 📚"
        )
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=msg)
            
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


message_lock = asyncio.Lock()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_sleep_window():
        await update.message.reply_text("💤 I am currently in Sleep Mode optimizing my brain. I will be back online at 7 AM ET!")
        return

    user_text = update.message.text
    chat_id   = update.effective_chat.id

    if update.message.reply_to_message and update.message.reply_to_message.text:
        reply_text = update.message.reply_to_message.text
        user_text = f"[In reply to your message: \"{reply_text}\"]\n\n{user_text}"

    # Send a "thinking" indicator
    thinking_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Thinking... (You are in a queue if you sent multiple messages)"
    )

    try:
        async with message_lock:
            reply = await send_to_antigravity_and_wait(user_text, chat_id)

        # Delete the thinking message
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
        except Exception:
            pass

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
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=thinking_msg.message_id,
                text=f"❌ An error occurred while processing your request: {e}"
            )
        except Exception:
            pass



async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    
    FREE_ALIASES = {
        "ultra": "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
        "nex": "openrouter:nex-agi/nex-n2-pro:free",
        "laguna": "openrouter:poolside/laguna-m.1:free",
        "gpt-oss": "openrouter:openai/gpt-oss-120b:free",
        "gemma": "openrouter:google/gemma-4-31b-it:free",
        "cohere": "openrouter:cohere/north-mini-code:free"
    }
    valid_local = ["flash", "pro", "flash_lite"]
    
    if not args:
        current = user_models.get(chat_id, "flash")
        display_current = current.replace("openrouter:", "") if current.startswith("openrouter:") else current
        alias_list = " | ".join([f"`/model {k}`" for k in FREE_ALIASES.keys()])
        await update.message.reply_text(
            f"Current model: *{display_current}*\n\n"
            f"*Private (G1) Models:* `/model flash` | `/model pro`\n"
            f"*Free OpenRouter Models:* {alias_list}\n\n"
            f"_(Note: OpenRouter endpoints are strictly hardcoded to the :free tier to guarantee zero charges)_",
            parse_mode="Markdown"
        )
        return
        
    requested = args[0].lower()
    
    # 1. Map alias to full OpenRouter model
    if requested in FREE_ALIASES:
        requested = FREE_ALIASES[requested]
        
    # 2. Check validity and ENFORCE :free safety
    if requested.startswith("openrouter:"):
        if not requested.endswith(":free"):
            requested += ":free" # Force the free endpoint so it never costs money
    elif requested not in valid_local:
        await update.message.reply_text("❌ Invalid model choice. Type `/model` to see available options.")
        return
        
    user_models[chat_id] = requested
    
    display_name = requested.replace("openrouter:", "") if requested.startswith("openrouter:") else requested
    await update.message.reply_text(f"Model safely switched to *{display_name}* ✅", parse_mode="Markdown")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Generating your summary digest... This might take a minute.")
    
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements, get_recent_google_docs
    from ai_processor import process_all_sources
    from notion_client import add_task_to_notion
    
    canvas = get_all_canvas_data() or "No Canvas"
    classroom = get_classroom_assignments() or "No Classroom"
    gmail = get_unread_emails() or "No Gmail"
    groupme = get_latest_messages("102851186") or "No GroupMe"
    announcements = get_classroom_announcements() or "No Announcements"
    docs = get_recent_google_docs() or "No Docs"
    
    ai_result = process_all_sources(canvas, classroom, gmail, groupme, classroom_ann_data=announcements, gdocs_data=docs)
    
    # Ask user before pushing tasks to Notion
    state = load_state()
    new_tasks = []
    for task in ai_result.get("tasks", []):
        thash = get_hash(task.get("id", task.get("title", "")))
        if thash not in state.setdefault("seen_tasks", []):
            new_tasks.append(task)
            state["seen_tasks"].append(thash)
    save_state(state)
    
    digest = ai_result.get("digest", "Nothing to report right now!")
    
    if new_tasks:
        tasks_str = ""
        for i, task in enumerate(new_tasks, 1):
            tasks_str += f"{i}. {task.get('title')} (Source: {task.get('source')})\n"
        digest += f"\n\n🚨 **NEW TASKS DETECTED** 🚨\n{tasks_str}\nShould I add these to Notion? If yes, reply with their priority (high/medium/low) and progress. If I should ignore any of them, let me know so I can learn!"
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
        
    # Ask to Compile Mega Study Guides
    topics = ai_result.get("topics", [])
    if topics:
        topics_str = "\n".join([f"- {t}" for t in topics])
        topic_msg = (
            f"🧠 **I detected you have upcoming assignments/tests for the following topics:**\n"
            f"{topics_str}\n\n"
            f"Would you like me to compile a Mega Study Guide for any of these? (Just reply 'Build a guide for...') 📚"
        )
        try:
            await context.bot.send_message(chat_id=chat_id, text=topic_msg, parse_mode="Markdown")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=topic_msg)


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
        # Run with root access via sudo
        sudo_pw = SUDO_PASSWORD or os.getenv('SUDO_PASSWORD', '')
        if sudo_pw:
            full_cmd = f"echo '{sudo_pw}' | sudo -S bash -c " + repr(cmd)
        else:
            full_cmd = "bash -c " + repr(cmd)
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

async def priority_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if len(context.args) != 2:
        await context.bot.send_message(chat_id=chat_id, text="Usage: `/p <short_id> <high/medium/low>`", parse_mode="Markdown")
        return
        
    short_id, priority = context.args[0], context.args[1].lower()
    if priority not in ["high", "medium", "low"]:
        await context.bot.send_message(chat_id=chat_id, text="Priority must be high, medium, or low.")
        return

    state = load_state()
    page_id = state.get("pending_priorities", {}).get(short_id)
    if not page_id:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Could not find pending task with ID `{short_id}`.", parse_mode="Markdown")
        return

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from notion_client import update_notion_task
    
    if update_notion_task(page_id, priority=priority):
        del state["pending_priorities"][short_id]
        save_state(state)
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Task priority updated to **{priority.capitalize()}** in Notion!", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Failed to update Notion.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads a photo sent to the bot, saves it, and asks the AI to process it."""
    chat_id = update.effective_chat.id
    if chat_id != 8534649457:
        await update.message.reply_text("❌ Unauthorized user.")
        return
        
    msg = await update.message.reply_text("📸 Downloading image...")
    
    # Get the largest resolution photo
    photo_file = await update.message.photo[-1].get_file()
    download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_homework.jpg")
    await photo_file.download_to_drive(download_path)
    
    caption = update.message.caption or ""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="🔍 Running local OCR (Tesseract)...")
    
    try:
        import pytesseract
        from PIL import Image
        ocr_text = pytesseract.image_to_string(Image.open(download_path))
        if not ocr_text.strip():
            ocr_text = "(No text found in image)"
    except Exception as e:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ OCR Error: {e}")
        return

    await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="🧠 Filtering with local Qwen2 model...")
    
    prompt = (
        "You are an offline filtering AI. Read the text extracted from this photo.\n"
        "Your job is to extract homework assignments, projects, or mandatory deadlines.\n"
        "If you see lists of numbers (e.g., 'Drills: 456, 460'), dates, or the word 'homework'/'due', you MUST extract them or reply 'UNSURE'.\n"
        "Only if you are 100% certain there is no actionable task, reply exactly with: 'NO_ALERT'\n"
        "CRITICAL RULE: If the text is messy and you cannot confidently parse it, reply exactly with: 'UNSURE'\n\n"
        f"Caption: {caption}\nPhoto OCR Text:\n{ocr_text}"
    )
    
    import httpx
    
    async def _call_ollama(model_name: str) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.0}
                    },
                    timeout=120.0
                )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass
        return ""

    try:
        extracted = await _call_ollama("qwen2:0.5b")
        if "UNSURE" in extracted.upper():
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="⚖️ 0.5B was unsure. Escalating to 3B model...")
            extracted = await _call_ollama("hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest")

        if extracted and "NO_ALERT" not in extracted.upper() and "UNSURE" not in extracted.upper():
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload ---\n{extracted}\n")
            reply = f"✅ Important text found and saved for the next digest!\n\n_Filtered preview:_\n{extracted}"
        else:
            # User specifically sent a photo, so it's important regardless of what the small model thinks.
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
            reply = "⚠️ Local AI couldn't parse specific assignments, but I saved the raw text for the cloud AI to review!"
    except Exception as e:
        reply = f"❌ Local LLM connection error: {e}"
        # Save raw OCR on error too
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
            f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
        
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text=reply, parse_mode="Markdown"
        )
    except Exception:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text=reply
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("build_guide_"):
        file_id = data.split("build_guide_")[1]
        chat_id = query.message.chat_id
        
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text="⏳ Downloading PDF, reading handwriting via Gemini Vision, and building Mega Study Guide... This will take a minute!"
        )
        
        # Run it synchronously since we are just blocking this callback (or ideally async, but this is fine for now)
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _build():
            from scrapers.mega_study_builder import build_guide_for_drive_file
            # Use a default topic like XA_MWF Notes
            return build_guide_for_drive_file(file_id, "XA_MWF Notes")
            
        try:
            # We must import from the current directory, but python might not know it
            import sys, os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from mega_study_builder import build_guide_for_drive_file
            
            result = await loop.run_in_executor(None, build_guide_for_drive_file, file_id, "XA_MWF Notes")
            
            try:
                await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=result)
                
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to build guide: {e}")

async def nightly_wrapper(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.nightly_processor import run_nightly_job
    from scrapers.memory_consolidation import consolidate_memory
    from scrapers.web_precacher import pre_cache_web
    
    try:
        await context.bot.send_message(chat_id=chat_id, text="💤 **Entering Sleep Cycle...** Executing nightly memory consolidation and pre-caching.", disable_notification=True)
        
        # 1. Process queued practice PDFs
        await run_nightly_job(context.bot, chat_id)
        
        # 2. Consolidate raw logs into curated_brain.md
        await consolidate_memory()
        
        # 3. Fetch tomorrow's research based on the new brain
        await pre_cache_web()
        
    except Exception as e:
        logger.error(f"Nightly sleep cycle error: {e}")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("Please set TELEGRAM_BOT_TOKEN in .env")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Auto-start the background 4-hour digest task for the user on boot
    SANEL_CHAT_ID = 8534649457
    job_queue = app.job_queue
    job_queue.run_repeating(check_updates, interval=14400, first=14400, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_digest")
    
    # Auto-start the 30-minute watchdog
    job_queue.run_repeating(watchdog_check, interval=1800, first=1800, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_watchdog")
    
    # Run the offline Llama PDF processor every night at 2:00 AM UTC
    import datetime
    import pytz
    et_tz = pytz.timezone('US/Eastern')
    job_queue.run_daily(nightly_wrapper, time=datetime.time(hour=1, minute=0, tzinfo=et_tz), chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_nightly")
    
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("bash", bash_command))
    app.add_handler(CommandHandler("p", priority_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Antigravity Telegram bridge is running...")
    app.run_polling()

import os
import json
import logging
import atexit
try:
    import telegram_logger
    telegram_logger.setup_telegram_logging()
except Exception:
    pass

from activity_log import log_event, log_llm_call, log_scrape, log_system, log_nightly, get_recent_events, format_events
from utils import scrub_pii
import time
import asyncio
import subprocess
import sys
import datetime
import pytz
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from bot.security import require_auth
from bot.commands import model_command, summary_command, bash_command, priority_command, ping_command, stats_command, backup_command, restore_command, correlations_command, classroom_pdfs_command, help_command, server_command, handle_callback

import config
import tempfile
from inline_keyboards import get_digest_topic_keyboard
from utils import correlate_items, enforce_all_rotations, create_backup
from voice_handler import transcribe_voice
from bot.runtime import _track_task, _cleanup_background_tasks

atexit.register(_cleanup_background_tasks)

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

# Ensure project root is on sys.path once (avoids repeated sys.path.append)
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)


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

from bot.ai_bridge import detect_topic, send_to_antigravity_and_wait




# ── Background Automation ──────────────────────────────────────────────────────

from bot.state import load_state, save_state, is_sleep_window, get_hash

async def watchdog_check(context: ContextTypes.DEFAULT_TYPE):
    if watchdog_lock.locked():
        logger.warning("watchdog already running, skipping")
        return
    async with watchdog_lock:
        await _watchdog_impl(context)


async def _watchdog_impl(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 30 mins to check for urgent anomalies using tiny local model Qwen2 0.5B."""
    if is_sleep_window(): return
    chat_id = context.job.chat_id
    state = load_state()
    # sys.path already set at module level
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
                loop = asyncio.get_running_loop()
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
        # Atomic write for nightly_queue.json
        import tempfile
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(nightly_queue_path), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding="utf-8") as f:
                json.dump(nightly_queue, f, indent=2)
            os.replace(tmp_path, nightly_queue_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        await context.bot.send_message(chat_id=chat_id, text=f"🛏️ Queued {len(nightly_queue)} new practice materials for processing offline tonight.")
    
    prompt = (
            "You are an urgent alert watchdog. Read the following recent school and email notifications.\n"
            "Look ONLY for critical anomalies or urgent updates (e.g., a sudden deadline extension, a direct message from a teacher, or an emergency alert).\n"
            "If you find something genuinely urgent, write a short 1-sentence warning about it.\n"
            "If there is nothing urgent, you MUST reply with exactly the word: NO_ALERT\n\n"
            f"DATA:\n{raw_data}"
        )
    try:
        from llm_router import call_openrouter
        from config import OR_FALLBACK_MODEL
        
        result = call_openrouter(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            prompt=f"Read the following recent school and email notifications. "
                  f"Look ONLY for critical anomalies or urgent updates. "
                  f"If there is nothing urgent, reply exactly: NO_ALERT\n\n"
                  f"DATA:\n{raw_data}",
            task="watchdog",
            fallback_chain=[OR_FALLBACK_MODEL],
            timeout=45,
        )

        # Send alert regardless of which model produced the result
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
    # Prevent overlapping executions if previous run takes >4 hours
    if digest_lock.locked():
        logger.warning("check_updates already running, skipping this tick")
        return

    async with digest_lock:
        await _check_updates_impl(context)


async def _check_updates_impl(context: ContextTypes.DEFAULT_TYPE):
    if is_sleep_window(): return
    chat_id = context.job.chat_id
    state = load_state()
    
    from scrapers.canvas_scraper import get_all_canvas_data
    from scrapers.groupme_scraper import get_latest_messages
    from scrapers.google_scraper import get_unread_emails, get_classroom_assignments, get_classroom_announcements, get_recent_google_docs
    from ai_processor import process_all_sources
    from scrapers.notion_client import add_task_to_notion, update_notion_task
    
    logger.info("Background job: Scraping sources...")
    
    # ── Per-source error recovery: each scraper runs independently ─────────
    async def _safe_scrape(name, func, *args):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args),
                timeout=60
            )
        except Exception as e:
            logger.error(f"Scraper {name} failed: {e}")
            return f"Error fetching {name}: {e}"

    c = await _safe_scrape("canvas", get_all_canvas_data)
    cl = await _safe_scrape("classroom", get_classroom_assignments)
    cla = await _safe_scrape("classroom_ann", get_classroom_announcements)
    gm = await _safe_scrape("gmail", get_unread_emails)
    grp = await _safe_scrape("groupme", get_latest_messages, "102851186")
    gd = await _safe_scrape("gdocs", get_recent_google_docs)

    logger.info("Background job: Processing with AI...")
    try:
        ai_result = await asyncio.to_thread(process_all_sources, c, cl, gm, grp, cla, gd)
    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Digest processing failed: {e}")
        return
    
    # 1. Notion Tasks
    import difflib
    new_tasks = []
    
    # Migrate old hash state to list of strings (hashes won't fuzzy match but we'll store new ones as strings)
    seen_titles = state.setdefault("seen_tasks", [])
    
    for task in ai_result.get("tasks", []):
        task_title = task.get("title", "").strip().lower()
        if not task_title: continue
        
        # Fuzzy match against seen tasks
        is_duplicate = False
        for seen in seen_titles:
            # If it's a legacy MD5 hash (length 32, hex), SequenceMatcher will just give 0.0 which is fine
            similarity = difflib.SequenceMatcher(None, task_title, seen).ratio()
            if similarity > 0.8:
                is_duplicate = True
                break
                
        if not is_duplicate:
            new_tasks.append(task)
            seen_titles.append(task_title)
            
    state["seen_tasks"] = seen_titles
    save_state(state)
    
    if new_tasks:
        tasks_str = ""
        for i, task in enumerate(new_tasks, 1):
            tasks_str += f"✅ **{task.get('title')}** (Source: {task.get('source')})\n"
            # Automatically push to Notion
            try:
                add_task_to_notion(
                    title=task.get('title'),
                    source=task.get('source'),
                    due_date=task.get('due_date'),
                    priority="medium",
                    status="Not started"
                )
            except Exception as e:
                logger.error(f"Failed to auto-push task to Notion: {e}")
        
        msg_text = f"🚨 **NEW TASKS ADDED TO NOTION** 🚨\n\n{tasks_str}\nI have automatically synced these to your Notion Tracker! Reply with their priority (high/medium/low) or current progress so I can update them."
        
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
        digest_msg = f"� **Periodic Digest**\n\n{digest}"
        max_len = 4096
        for i in range(0, len(digest_msg), max_len):
            chunk = digest_msg[i:i+max_len]
            try:
                await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            
    # 3. Ask to Compile Mega Study Guides (with inline keyboard)
    topics = ai_result.get("topics", [])
    if topics:
        topics_str = "\n".join([f"- {t}" for t in topics])
        msg = (
            f"🧠 **I detected you have upcoming assignments/tests for the following topics:**\n"
            f"{topics_str}\n\n"
            f"Would you like me to compile a Mega Study Guide for any of these? 📚"
        )
        keyboard = get_digest_topic_keyboard(topics)
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=msg)

    # 4. Track correlations across sources
    try:
        correlate_items([
            {"source": "canvas", "title": t, "type": "assignment"}
            for t in ai_result.get("topics", [])
        ] + [
            {"source": "gmail", "title": e.get("title", ""), "type": "email"}
            for e in ai_result.get("tasks", [])
        ])
    except Exception as e:
        logger.warning(f"Correlation tracking failed: {e}")

    state["seen_tasks"] = state.get("seen_tasks", [])[-config.MAX_SEEN_TASKS:]
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


# ── Concurrency Locks ─────────────────────────────────────────────────────────
from bot.state import is_sleep_window, get_user_lock
digest_lock = asyncio.Lock()  # prevents overlapping check_updates
watchdog_lock = asyncio.Lock()  # prevents overlapping watchdog


# ── Telegram handlers ──────────────────────────────────────────────────────────

@require_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_sleep_window():
        await update.message.reply_text("💤 I am currently in Sleep Mode optimizing my brain. I will be back online at 7 AM ET!")
        return

    user_text = update.message.text
    chat_id   = update.effective_chat.id

    if user_text.strip().lower() in ("help", "commands", "what can you do", "cmds", "/help", "/"):
        await help_command(update, context)
        return

    if user_text.strip().lower() == "models":
        context.args = []
        await model_command(update, context)
        return

    if update.message.reply_to_message and update.message.reply_to_message.text:
        reply_text = update.message.reply_to_message.text
        user_text = f"[In reply to your message: \"{reply_text}\"]\n\n{user_text}"

    # Send a "thinking" indicator
    thinking_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Thinking... (You are in a queue if you sent multiple messages)"
    )

    try:
        user_lock = get_user_lock(chat_id)
        async with user_lock:
            reply = await send_to_antigravity_and_wait(user_text, chat_id, context, thinking_msg)
            
        log_event("message", {"preview": user_text[:50], "routed_to": "unknown"}, notify=False)

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
        log_event("error", {"message": str(e)[:80], "source": "handle_message"})
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=thinking_msg.message_id,
                text=f"❌ An error occurred while processing your request: {e}"
            )
        except Exception:
            pass



@require_auth
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download voice message, transcribe locally, route through AI."""
    chat_id = update.effective_chat.id
    if chat_id != config.SANEL_CHAT_ID:
        await update.message.reply_text("")
        return

    msg = await update.message.reply_text("🎤 Transcribing voice message...")

    try:
        voice_file = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await voice_file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        transcription = transcribe_voice(tmp_path)
        os.unlink(tmp_path)

        if transcription.startswith("❌"):
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=transcription)
            return

        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id,
            text=f"� Transcribed: \"{transcription[:200]}{'...' if len(transcription) > 200 else ''}\"\n\nThinking..."
        )

        # Route transcription through the AI
        user_lock = get_user_lock(chat_id)
        async with user_lock:
            reply = await send_to_antigravity_and_wait(transcription, chat_id, context, msg)

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        except Exception:
            pass

        for i in range(0, len(reply), 4096):
            try:
                await context.bot.send_message(chat_id=chat_id, text=reply[i:i+4096], parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=reply[i:i+4096])

    except Exception as e:
        logger.error(f"Error handling voice: {e}")
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ Error: {e}")
        except Exception:
            pass


@require_auth
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads a photo sent to the bot, saves it, and asks the AI to process it."""
    chat_id = update.effective_chat.id
        
    msg = await update.message.reply_text("📸 Downloading image...")
    
    # Get the largest resolution photo
    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        download_path = tmp.name
    await photo_file.download_to_drive(download_path)
    
    caption = update.message.caption or ""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="🔍 Running local OCR (Tesseract)...")
    
    try:
        import pytesseract
        from PIL import Image
        ocr_text = pytesseract.image_to_string(Image.open(download_path))
        if not ocr_text.strip():
            ocr_text = "(No text found in image)"
        log_event("photo", {"ocr_chars": len(ocr_text), "has_question": bool(caption.strip())}, notify=False)
    except Exception as e:
        log_event("error", {"message": str(e)[:80], "source": "ocr"})
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ OCR Error: {e}")
        return

    # If the user asked a question in the caption, route the OCR text into the primary AI so it can use the PDFs
    if caption.strip():
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="🧠 Analyzing your question using the Knowledge Base & PDFs...")
        user_text = f"[I have uploaded a photo. Here is the exact text written in the photo:\n{ocr_text}]\n\nMy Question: {caption}"
        try:
            user_lock = get_user_lock(chat_id)
            async with user_lock:
                reply = await send_to_antigravity_and_wait(user_text, chat_id, context, msg)
                
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            except Exception:
                pass
                
            max_len = 4096
            for i in range(0, len(reply), max_len):
                try:
                    await context.bot.send_message(chat_id=chat_id, text=reply[i:i+max_len], parse_mode="Markdown")
                except Exception:
                    await context.bot.send_message(chat_id=chat_id, text=reply[i:i+max_len])
            return
        except Exception as e:
            logger.error(f"Error answering photo question: {e}")
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ Error analyzing photo: {e}")
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
    
    from llm_router import call_openrouter
    try:
        extracted = call_openrouter(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            prompt=prompt,
            task="photo-extract",
            fallback_chain=["meta-llama/llama-3.3-70b-instruct:free"],
            timeout=120,
        )
    except Exception:
        logger.info("Falling back to G1 Flash for photo extraction...")
        from ai_processor import call_agy
        import asyncio
        try:
            extracted = await asyncio.to_thread(call_agy, prompt, 3600, "flash")
        except Exception as e:
            reply = f"❌ Local LLM connection error: {e}"
            extracted = None
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
                
            # Add to the most recently active chat history so the user can ask follow-up questions!
            import glob
            history_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chat_history_{chat_id}_*.txt"))
            if history_files:
                latest_file = max(history_files, key=os.path.getmtime)
                with open(latest_file, "a") as f:
                    f.write(f"User: [I just uploaded a photo. Here is the raw text extracted from it: {ocr_text}]\\nModel: (Image received. I am ready for questions about it.)\\n\\n")
    
    if extracted:
        if "NO_ALERT" not in extracted.upper() and "UNSURE" not in extracted.upper():
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload ---\n{extracted}\n")
            reply = f"✅ Important text found and saved for the next digest!\n\n_Filtered preview:_\n{extracted}"
            import glob
            history_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chat_history_{chat_id}_*.txt"))
            if history_files:
                latest_file = max(history_files, key=os.path.getmtime)
                with open(latest_file, "a") as f:
                    f.write(f"User: [I just uploaded a photo. Here is the raw text extracted from it: {ocr_text}]\\nModel: (Image received. I am ready for questions about it.)\\n\\n")
        else:
            # User specifically sent a photo, so it's important regardless of what the small model thinks.
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
            reply = "⚠️ Local AI couldn't parse specific assignments, but I saved the raw text for the cloud AI to review!"
        
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text=reply, parse_mode="Markdown"
        )
    except Exception:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text=reply
        )

async def nightly_wrapper(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scrapers.nightly_processor import run_nightly_job
    from scrapers.memory_consolidation import consolidate_memory
    from scrapers.web_precacher import pre_cache_web
    
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text="💤 **Entering Sleep Cycle...** Initiating nightly background tasks.", disable_notification=True)
        
        # 1. Process queued practice PDFs
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n1️⃣ Processing queued OCR/Practice PDFs...", parse_mode="Markdown")
        except Exception: pass
        await run_nightly_job(context.bot, chat_id)
        
        # 2. Consolidate raw logs into curated_brain.md
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n✅ PDFs Processed.\n2️⃣ Consolidating short-term memory into `curated_brain.md`...", parse_mode="Markdown")
        except Exception: pass
        await consolidate_memory()
        
        # 3. Fetch tomorrow's research based on the new brain
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n✅ Memory Consolidated.\n3️⃣ Pre-caching tomorrow's research from the web...", parse_mode="Markdown")
        except Exception: pass
        await pre_cache_web()
        
        from config import BASE_DIR
        python_bin = sys.executable
        builder_script = os.path.join(BASE_DIR, 'run_builder.py')
        
        # 4. Auto-Generate SAT Guides
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n✅ Web Pre-cached.\n4️⃣ Building Separated SAT Study Guides (Math, Reading, Writing)...", parse_mode="Markdown")
        except Exception: pass
        await asyncio.to_thread(subprocess.run, [python_bin, builder_script, 'SAT Math and Geometry Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.to_thread(subprocess.run, [python_bin, builder_script, 'SAT Reading Comprehension Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.to_thread(subprocess.run, [python_bin, builder_script, 'SAT Writing and Grammar Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 5. Dynamic Daily Topic Guide
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n✅ SAT Guide Built.\n5️⃣ Analyzing today's notes to build a dynamic subject guide...", parse_mode="Markdown")
        except Exception: pass
        
        from ai_processor import call_agy
        pdf_exports_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "pdf_exports.txt")
        dynamic_topic = "General Knowledge"
        if os.path.exists(pdf_exports_file):
            with open(pdf_exports_file, "r") as f:
                recent_text = f.read().strip()[-5000:]
            if recent_text:
                dynamic_topic = call_agy(f"Based on these study notes, extract the single most specific 1-4 word subject or topic being studied. Respond ONLY with the topic name. Notes: {recent_text}", model="flash")
                if not dynamic_topic or len(dynamic_topic) > 50:
                    dynamic_topic = "General Academic Concepts"
                    
        await asyncio.to_thread(subprocess.run, [python_bin, builder_script, dynamic_topic], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"💤 **Sleep Cycle Complete:**\n✅ PDFs Processed\n✅ Memory Consolidated\n✅ Web Pre-cached\n✅ SAT Guide Updated\n✅ '{dynamic_topic}' Guide Generated!\n\nGood night! 🌙", parse_mode="Markdown")
        except Exception: pass
        
    except Exception as e:
        logger.error(f"Nightly sleep cycle error: {e}")

# ── NEW COMMAND HANDLERS ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("Please set TELEGRAM_BOT_TOKEN in .env")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Auto-start the background 4-hour digest task for the user on boot
    SANEL_CHAT_ID = config.SANEL_CHAT_ID
    job_queue = app.job_queue
    
    # Enforce rotations and compile context before first run
    try:
        enforce_all_rotations()
    except Exception as e:
        logger.warning(f"Initial rotation enforcement failed: {e}")

    try:
        from scrapers.compile_context import compile_bot_context
        asyncio.get_event_loop().run_until_complete(compile_bot_context())
    except Exception as e:
        logger.error(f"Failed to pre-compile bot context: {e}")
    
    import time as _time
    try:
        last_mtime = os.path.getmtime(config.LATEST_DIGEST_FILE)
        elapsed = _time.time() - last_mtime
        time_until_next = max(5, int(config.DIGEST_INTERVAL_SECONDS - elapsed))
    except Exception:
        time_until_next = 5
        
    job_queue.run_repeating(check_updates, interval=config.DIGEST_INTERVAL_SECONDS, first=time_until_next, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_digest")
    
    # Run rotation enforcement every 6 hours
    job_queue.run_repeating(lambda ctx: enforce_all_rotations(), interval=21600, first=21600, chat_id=SANEL_CHAT_ID, name="rotation_enforcement")

    # Daily backup at 3 AM ET
    job_queue.run_daily(
        lambda ctx: create_backup(),
        time=datetime.time(hour=3, minute=0, tzinfo=pytz.timezone('US/Eastern')),
        chat_id=SANEL_CHAT_ID, name="daily_backup"
    )
    
    async def morning_wrapper(context: ContextTypes.DEFAULT_TYPE):
        try:
            from scrapers.morning_digest import send_morning_digest
            await send_morning_digest()
        except Exception as e:
            logger.error(f"Morning digest error: {e}")
            
    # Auto-start the 30-minute watchdog
    job_queue.run_repeating(watchdog_check, interval=config.WATCHDOG_INTERVAL_SECONDS, first=1800, chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_watchdog")
    
    # Run the offline Llama PDF processor every night at 2:00 AM ET
    job_queue.run_daily(nightly_wrapper, time=datetime.time(hour=1, minute=0, tzinfo=pytz.timezone('US/Eastern')), chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_nightly")
    
    # Run the Morning Digest every morning at 7:00 AM ET
    job_queue.run_daily(morning_wrapper, time=datetime.time(hour=7, minute=0, tzinfo=pytz.timezone('US/Eastern')), chat_id=SANEL_CHAT_ID, name=f"{SANEL_CHAT_ID}_morning")
    
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("bash", bash_command))
    app.add_handler(CommandHandler("p", priority_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("restore", restore_command))
    app.add_handler(CommandHandler("correlations", correlations_command))
    app.add_handler(CommandHandler("classroom", classroom_pdfs_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("server", server_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))



    print("🤖 Antigravity Telegram bridge is running...")

    # Run with graceful shutdown
    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Bot stopped. Rotating files before exit...")
        enforce_all_rotations()

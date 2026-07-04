import os
import json
import logging
import atexit
try:
    import telegram_logger
    telegram_logger.setup_telegram_logging()
except:
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

# ── Background Task Tracking ───────────────────────────────────────────────────
# Track all background tasks for proper cleanup on shutdown
_background_tasks: set[asyncio.Task] = set()

def _track_task(task: asyncio.Task) -> asyncio.Task:
    """Add task to tracking set and auto-remove when done."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

def _cleanup_background_tasks():
    """Cancel all tracked background tasks on exit."""
    if _background_tasks:
        logger.info(f"Cancelling {len(_background_tasks)} background tasks...")
        for task in _background_tasks:
            if not task.done():
                task.cancel()
        # Note: we don't await here since this runs at exit

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
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [AGENTAPI_BIN, "--model", "Gemini 3.5 Flash (Low)", "--dangerously-skip-permissions", "--print", prompt],
                    capture_output=True, text=True, timeout=30
                )
            ),
            timeout=35
        )
        topic = result.stdout.strip().lower()
        topic = re.sub(r'[^a-z0-9_]', '', topic.replace(' ', '_'))
        if len(topic) > 30:
            logger.warning(f"Topic name too long from flash_lite model, falling back to 'general': {topic}")
            return "general"
        return topic if topic else "general"
    except Exception as e:
        logger.error(f"Topic detection failed: {e}")
        return "general"


# ── Bridge logic ───────────────────────────────────────────────────────────────

async def send_to_antigravity_and_wait(user_message: str, chat_id: int = 0, context=None, status_msg=None) -> str:
    """Uses agy --print for a direct response. Works standalone on Debian."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_digest.txt"), "r") as f:
            digest_context = f.read()
    except Exception:
        digest_context = "No recent data available."
        
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_context.txt"), "r") as f:
            brain_context = f.read()
    except Exception:
        brain_context = "No offline memory consolidated yet."

    if status_msg and context:
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="🔍 Classifying topic...")
        except Exception: pass
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
        f"When Sanel asks you to DO something on the server, you MUST instead wrap the shell command in angle-bracket BASH tags like this:\n"
        f"[BASH]your command here[/BASH] (Note: Use angle brackets <> instead of square brackets [])\n"
        f"The system's python wrapper will automatically parse these tags and run that command as root, then show you the output in the next turn. "
        f"You can chain multiple commands. Always include the angle-bracket BASH tags when action is needed.\n\n"
    )

    capabilities_str = (
        "OTHER CAPABILITIES:\n"
        "--- SERVER MANAGEMENT ---\n"
        "- Server Status: Check system resources via bash [BASH]free -h && uptime && ps aux | head -n 10[/BASH]\n"
        "- Embedding Progress: Check the offline indexer via bash [BASH]tail -n 20 /tmp/embed_build4.log[/BASH]\n"
        "- Minecraft Server: Check MC via bash [BASH]ps aux | grep paper.jar | grep -v grep || echo 'MC stopped'[/BASH], start [BASH]bash /home/sanel/mc_server/start_mc.sh[/BASH], stop [BASH]tmux send-keys -t minecraft 'stop' C-m[/BASH]\n"
        "- Activity Log: Check recent bot events via bash [BASH]python3 -c 'from activity_log import get_recent_events, format_events; print(format_events(get_recent_events(10)))'[/BASH]\n\n"
        "--- ACADEMIC & STUDY ---\n"
        "- STUDY COMPANION: If Sanel asks you to build a study guide, find a YouTube video for a topic, or research something to study, you MUST use the mega study builder script via bash:\n"
        "[BASH]python3 -c 'from mega_study_builder import generate_mega_guide; print(generate_mega_guide(\"Topic Name Here\"))'[/BASH]\n"
        "- DEEP-DIVE KNOWLEDGE BASE: An offline researcher runs every night to compile massive study sheets on your current topics. If Sanel asks a question about an academic topic, check if a guide exists by using bash to list and read files in `/home/sanel/personal-assistant-bot/knowledge_base/` before answering, so you can interact and research much faster!\n"
        "- KNOWLEDGE GAP TRACKING: If you are grading an answer or helping Sanel with a problem and you notice a weakness (e.g. \"struggles with polynomial factoring\"), you MUST log this to a text file using bash: `echo 'Struggles with factoring when a > 1' >> /home/sanel/personal-assistant-bot/knowledge_gaps/math.txt` so the offline researcher can heavily target his weak points tonight.\n\n"
        "--- LIFE MANAGEMENT ---\n"
        "- Every 4 hours: auto-digest from Canvas, Classroom, Gmail, GroupMe\n"
        "- Notion: assignments auto-pushed to Tasks Tracker\n"
        "- Natural Language Notion Pushes: When the background job alerts Sanel about a NEW task and asks him for priority/status, you MUST push it to Notion using the add_task_to_notion python script when he replies! Example:\n"
        "[BASH]python3 -c 'from notion_client import add_task_to_notion; add_task_to_notion(title=\"Math Homework\", priority=\"high\", status=\"Not started\", start_value=0, end_value=100)'[/BASH]\n"
        "- CALENDAR SCHEDULING: If Sanel asks you to schedule a study session, block off time, or add something to his calendar, you MUST use the calendar manager via bash. Calculate the start time in ISO format based on his request and current time:\n"
        "[BASH]python3 -c 'from scrapers.calendar_manager import add_study_session; print(add_study_session(\"Task Name\", \"2026-06-20T14:00:00\", 120))'[/BASH] (Remember: Use angle brackets <> instead of [])\n"
        "- DYNAMIC LEARNING: If Sanel is answering a question about whether a certain type of message, email, or topic is important to track or ignore, you MUST save this rule to the local memory so the local filter AI can use it in the future. To do this, use a bash command:\n"
        "[BASH]echo 'Ignore all emails from XYZ' >> /home/sanel/personal-assistant-bot/learning_rules.txt[/BASH]\n"
        "- VERIFICATION CUSTOMIZATION: If Sanel gives you custom instructions on how the Verification Agent should behave (e.g. telling it to auto-fix errors instead of summarizing them), you MUST save his instructions using bash: `echo 'Auto-fix syntax errors' >> /home/sanel/personal-assistant-bot/verification_rules.txt`.\n\n"
        "--- BE PROACTIVE ---\n"
        "- Do not wait for permission. If the user asks about the server, check it! If the user asks about Minecraft, check its status and offer to start it! Take initiative.\n\n"
        "- /summary: manual digest trigger | /server: server dashboard | /bash <cmd>: run commands directly\n\n"
    )

    system = system + capabilities_str + (
        f"Here is the core context of your life and active classes (from your compressed Memory Index):\n\n{brain_context}\n\n"
        f"Here is the latest live data digest:\n\n{digest_context}\n\n"
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

    # Add semantic retrieval for academic questions
    retrieval_context = ""
    try:
        from scrapers.semantic_retrieval import get_context_for_prompt
        retrieval_result = get_context_for_prompt(user_message, top_k=5)
        if retrieval_result and "SEMANTIC RETRIEVAL" in retrieval_result:
            retrieval_context = f"\n\n=== SEMANTIC RETRIEVAL FROM KNOWLEDGE BASE ===\n{retrieval_result}\n=== END RETRIEVAL ===\n"
            logger.info(f"Semantic retrieval added to prompt for: {user_message[:50]}")
    except Exception as e:
        logger.warning(f"Semantic retrieval failed: {e}")

    full_prompt = (system + "\n\n"
                   f"--- {topic.upper()} CONVERSATION HISTORY ---\n"
                   + chat_history +
                   f"\n--- END HISTORY ---\n"
                   + retrieval_context +
                   f"\nUser: " + user_message)
    
    model = user_models.get(chat_id, "auto")
    
    if model == "auto":
        if status_msg and context:
            try: await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="🛡️ Running local PII privacy filter...")
            except Exception: pass
        logger.info("Running PII privacy filter via flash...")
        privacy_prompt = (
            "Analyze the following conversation context. Does it contain ANY highly personal "
            "information (e.g. real names, personal emails, physical addresses, private academic grades, "
            "bank details, or intimate personal stories)?\n\n"
            f"Context to check:\n{chat_history[-1000:]}\n\nUser: {user_message}\n\n"
            "Reply with EXACTLY ONE WORD: 'YES' if it contains personal info, or 'NO' if it is safe general/academic knowledge."
        )
        try:
            p_result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", privacy_prompt],
                        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL
                    )
                ),
                timeout=65
            )
            is_private = "yes" in p_result.stdout.lower()
        except Exception as e:
            logger.error(f"Privacy filter failed, defaulting to secure: {e}")
            is_private = True # Fail safe
            
        if is_private:
            logger.info("Auto-routing to FLASH (PII detected)")
            model = "flash"
        else:
            if len(user_message) > 300:
                logger.info("Auto-routing to NEMOTRON (Long/Complex query)")
                model = "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"
            else:
                from config import OR_FALLBACK_MODEL
                logger.info(f"Auto-routing to fallback model ({OR_FALLBACK_MODEL}) (Short/Academic query)")
                model = f"openrouter:{OR_FALLBACK_MODEL}"
    
    out = ""
    actual_model_used = model
    if model.startswith("openrouter:"):
        or_model_name = model.split("openrouter:", 1)[1]
        logger.info(f"OpenRouter model={or_model_name}: {user_message[:60]}")
        log_llm_call(or_model_name, "chat", 0, is_local=False)
        import httpx
        
        async def _call_or(m_name):
            import time
            import json
            full_response = ""
            current_thought = ""
            in_thought = False
            last_edit_time = 0
            
            # SECURITY: Scrub PII from all cloud-bound data
            scrubbed_system = scrub_pii(system, aggressive=True)
            scrubbed_chat_history = scrub_pii(chat_history, aggressive=True)
            scrubbed_user_message = scrub_pii(user_message, aggressive=True)
            
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=5.0)) as client:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                            "HTTP-Referer": "https://github.com/SanelL112/Antigravity-Based-Assistant-Bot",
                            "X-Title": "Antigravity-Based-Assistant-Bot"
                        },
                        json={
                            "model": m_name,
                            "stream": True,
                            "messages": [
                                {"role": "system", "content": scrubbed_system + "\n\nCRITICAL: Before answering, you MUST think step-by-step and wrap your internal thought process in <thought>...</thought> tags."},
                                {"role": "user", "content": f"--- {topic.upper()} CONVERSATION HISTORY ---\n{scrubbed_chat_history}\n--- END HISTORY ---\n\nUser: {scrubbed_user_message}"}
                            ]
                        },
                        timeout=180.0
                    ) as resp:
                        if resp.status_code != 200:
                            return None
                            
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                if line.strip() == "data: [DONE]":
                                    break
                                try:
                                    chunk = json.loads(line[6:])
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_response += content
                                        
                                        if "<thought>" in full_response and "</thought>" not in full_response:
                                            in_thought = True
                                            current_thought = full_response.split("<thought>")[-1]
                                        elif "</thought>" in full_response:
                                            in_thought = False
                                            
                                        now = time.time()
                                        if now - last_edit_time > 1.5:
                                            last_edit_time = now
                                            if status_msg and context:
                                                try:
                                                    if in_thought:
                                                        disp = current_thought[-400:].strip()
                                                        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 **Thinking...**\n_{disp}_", parse_mode="Markdown")
                                                    else:
                                                        final_text = full_response.split("</thought>")[-1] if "</thought>" in full_response else full_response
                                                        disp = final_text[-800:].strip()
                                                        if disp:
                                                            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"✍️ **Typing...**\n{disp}")
                                                except Exception:
                                                    pass
                                except Exception:
                                    pass
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                return None
                
            if "</thought>" in full_response:
                return full_response.split("</thought>")[-1].strip()
            return full_response.strip()
                
        try:
            if status_msg and context:
                try: await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 Generating response using {or_model_name}...")
                except Exception: pass
            out = await _call_or(or_model_name)
            actual_model_used = or_model_name
            fail_phrases = ["i cannot", "i'm sorry", "i don't know", "as an ai", "unable to", "i apologize"]
            if not out or (isinstance(out, str) and any(p in out.lower()[:50] for p in fail_phrases)):
                if or_model_name == "nvidia/nemotron-3-ultra-550b-a55b:free":
                    from config import OR_FALLBACK_MODEL
                    logger.warning(f"Nemotron failed or refused. Falling back to {OR_FALLBACK_MODEL}...")
                    fallback_out = await _call_or(OR_FALLBACK_MODEL)
                    if fallback_out and not any(p in fallback_out.lower()[:50] for p in fail_phrases):
                        out = fallback_out
                        actual_model_used = OR_FALLBACK_MODEL
                    else:
                        logger.warning("Fallback failed or refused. Falling back to local G1 Flash...")
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: subprocess.run([AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", full_prompt], capture_output=True, text=True, timeout=RESPONSE_TIMEOUT, stdin=subprocess.DEVNULL)
                            ), timeout=RESPONSE_TIMEOUT + 5)
                        out = result.stdout.strip()
                        actual_model_used = "flash (local fallback)"
        except Exception as e:
            if or_model_name == "nvidia/nemotron-3-ultra-550b-a55b:free":
                from config import OR_FALLBACK_MODEL
                logger.warning(f"Nemotron exception ({e}). Falling back to {OR_FALLBACK_MODEL}...")
                try:
                    out = await _call_or(OR_FALLBACK_MODEL)
                    actual_model_used = OR_FALLBACK_MODEL
                    if not out: raise Exception(f"{OR_FALLBACK_MODEL} empty")
                except Exception as e2:
                    logger.warning(f"{OR_FALLBACK_MODEL} exception ({e2}). Falling back to local G1 Flash...")
                    try:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: subprocess.run([AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", full_prompt], capture_output=True, text=True, timeout=RESPONSE_TIMEOUT, stdin=subprocess.DEVNULL)
                            ), timeout=RESPONSE_TIMEOUT + 5)
                        out = result.stdout.strip()
                        actual_model_used = "flash (local fallback)"
                    except Exception as e3:
                        out = f"⚠️ Fallback to G1 Exception: {e3}"
            else:
                out = f"⚠️ OpenRouter Exception: {e}"
                
        if not out:
            out = "⚠️ OpenRouter returned an empty response or failed."
    else:
        if status_msg and context:
            try: await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 Generating response using local {model}...")
            except Exception: pass
        logger.info(f"agy --print model={model}: {user_message[:60]}")
        log_llm_call(f"agy/{model}", "chat", 0, is_local=True)
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

    if out and not out.startswith("⚠️"):
        logger.info("Response generated successfully.")
        # Lightweight sanity check: only run on responses that look suspicious
        # (very short, contain error markers, or look like raw system output)
        _suspicious = (
            len(out.strip()) < 20
            or "error" in out.lower()[:100] and "bash" not in out.lower()[:100]
            or out.strip().startswith(("[", "{", "Traceback", "Error:"))
            or "I cannot" in out and len(out.strip()) < 50
        )
        if _suspicious:
            logger.warning("Response looks suspicious, running quick sanity check...")
            try:
                sanity_prompt = (
                    "You are a quality-control filter. Does this AI response look coherent and helpful?\n\n"
                    f"RESPONSE: {out[:500]}\n\n"
                    "Reply YES if coherent, NO if broken/hallucinated."
                )
                sanity_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: subprocess.run(
                            [AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", sanity_prompt],
                            capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL
                        )
                    ),
                    timeout=20
                )
                if "no" in sanity_result.stdout.lower() and "yes" not in sanity_result.stdout.lower()[:5]:
                    logger.warning("Sanity check flagged response as broken. Running recovery agent...")
                    log_event("error", {"message": "AI response failed sanity check, running recovery", "source": "sanity_filter"})
                    recovery_prompt = (
                        "You are a Recovery AI Agent. The primary AI model hallucinated or produced broken output.\n\n"
                        f"USER REQUEST:\n{user_message}\n\n"
                        f"BROKEN OUTPUT:\n{out[:2000]}\n\n"
                        "Your job is to provide a clear, coherent, correct response. Do not apologize, just answer correctly. "
                        "Use [BASH] tags if you need to run commands."
                    )
                    try:
                        recovery_result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: subprocess.run(
                                    [AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", recovery_prompt],
                                    capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL
                                )
                            ),
                            timeout=65
                        )
                        recovered_text = recovery_result.stdout.strip()
                        if recovered_text:
                            out = recovered_text
                            actual_model_used = "flash (Recovery Agent)"
                            logger.info("Recovery agent produced a corrected response.")
                        else:
                            out = "⚠️ The AI hallucinated and the Recovery Agent failed to fix it. Please try again."
                    except Exception as e:
                        logger.error(f"Recovery agent timeout or error: {e}")
                        out = "⚠️ The AI hallucinated and the Recovery Agent timed out. Please try your request again."
                else:
                    logger.info("Sanity check passed.")
            except Exception:
                pass  # Don't let sanity check failures block responses

    if out and not out.startswith("⚠️"):
        disp_model = actual_model_used.replace("openrouter:", "") if "openrouter" in actual_model_used else actual_model_used
        out += f"\n\n_(Generated by: `{disp_model}`)_"

    # Auto-execute any <BASH>...</BASH> blocks in the response
    import re as _re
    
    # BASH execution now uses run_bash_safely from utils (with audit log + rate limit)

    def _replace_bash(m):
        cmd = m.group(1).strip()
        logger.info(f"Auto-executing: {cmd[:80]}")
        output = run_bash_safely(cmd, chat_id=chat_id)
        return f"\n💻 `{cmd}`\n```\n{output}\n```"

    original_out = out
    out = _re.sub(r'<BASH>(.*?)</BASH>', _replace_bash, out, flags=_re.DOTALL)
    out = _re.sub(r'\[BASH\](.*?)\[/BASH\]', _replace_bash, out, flags=_re.DOTALL)

    if original_out != out and "\n```\n" in out:
        logger.info("Command executed. Dispatching Verification Agent...")
        
        custom_instructions = ""
        vrules = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verification_rules.txt")
        if os.path.exists(vrules):
            with open(vrules, "r") as f:
                custom_instructions = f"\n\nCRITICAL CUSTOM INSTRUCTIONS FROM USER:\n{f.read()}"
                
        summary_prompt = (
            "You are a Verification AI Agent. You just executed a background system command on behalf of the user.\n\n"
            f"USER REQUEST:\n{user_message}\n\n"
            f"COMMAND AND OUTPUT:\n{out[-3000:]}\n\n"
            "Your job is to read the output of the command you just ran, and give the user a quick, natural summary "
            "confirming whether the task succeeded, failed, or what the exact result was. "
            "Speak directly to the user. Do not use any bash tags. Keep it concise."
            f"{custom_instructions}"
        )
        async def _run_verification_bg(prompt_text, chat_id_to_notify):
            try:
                # Use default fallback model as requested, taking as much time as needed (up to 300s)
                from config import OR_FALLBACK_MODEL
                res = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: subprocess.run(
                            [AGENTAPI_BIN, "--model", f"openrouter:{OR_FALLBACK_MODEL}", "--dangerously-skip-permissions", "--print", prompt_text],
                            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL
                        )
                    ),
                    timeout=310
                )
                summary_text = res.stdout.strip()
                if summary_text:
                    await context.bot.send_message(chat_id=chat_id_to_notify, text=f"🤖 **Verification ({OR_FALLBACK_MODEL}):**\n{summary_text}", parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Verification Agent timeout or error: {e}")

        if context:
            # Tell the user we are verifying in the background
            _track_task(asyncio.create_task(_run_verification_bg(summary_prompt, chat_id)))
        else:
            # Fallback for CLI standalone mode
            try:
                from config import OR_FALLBACK_MODEL
                summary_result = subprocess.run([AGENTAPI_BIN, "--model", f"openrouter:{OR_FALLBACK_MODEL}", "--dangerously-skip-permissions", "--print", summary_prompt], capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
                summary_text = summary_result.stdout.strip()
                if summary_text:
                    out += f"\n\n🤖 **Verification:**\n{summary_text}"
            except Exception as e:
                logger.error(f"Summary agent error: {e}")

    # Append turn to custom history file (with atomic write + rotation)
    try:
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(f"User: {user_message}\nModel: {out}\n\n")
        # Rotate if file exceeds 50KB to prevent unbounded growth
        if os.path.getsize(history_file) > 50000:
            with open(history_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Atomic write: write to temp then rename
            import tempfile
            fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(history_file), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding="utf-8") as f:
                    f.write(content[-40000:])  # Keep last 40KB
                os.replace(tmp_path, history_file)
                logger.info(f"Rotated history file: {os.path.basename(history_file)}")
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
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
    """Atomic write: write to temp file then rename (prevents corruption on crash)."""
    import tempfile
    try:
        fd, tmp_path = tempfile.mkstemp(dir=STATE_FILE.parent, suffix='.tmp')
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STATE_FILE)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        # Fallback to direct write (better than nothing)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

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
    from notion_client import add_task_to_notion, update_notion_task
    
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
message_lock = asyncio.Lock()
digest_lock = asyncio.Lock()  # prevents overlapping check_updates
watchdog_lock = asyncio.Lock()  # prevents overlapping watchdog


# ── Telegram handlers ──────────────────────────────────────────────────────────

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
        async with message_lock:
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



async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    
    FREE_ALIASES = {
        "llama3.3": "openrouter:meta-llama/llama-3.3-70b-instruct:free",
        "llama3.2": "openrouter:meta-llama/llama-3.2-3b-instruct:free",
        "hermes": "openrouter:nousresearch/hermes-3-llama-3.1-405b:free",
        "ultra": "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
        "nemotron-super": "openrouter:nvidia/nemotron-3-super-120b-a12b:free",
        "nemotron-safety": "openrouter:nvidia/nemotron-3.5-content-safety:free",
        "nemotron-nano": "openrouter:nvidia/nemotron-3-nano-30b-a3b:free",
        "nemotron-omni": "openrouter:nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "nemotron-vl": "openrouter:nvidia/nemotron-nano-12b-v2-vl:free",
        "nemotron-9b": "openrouter:nvidia/nemotron-nano-9b-v2:free",
        "nex": "openrouter:nex-agi/nex-n2-pro:free",
        "laguna": "openrouter:poolside/laguna-m.1:free",
        "laguna-xs": "openrouter:poolside/laguna-xs.2:free",
        "gpt-oss": "openrouter:openai/gpt-oss-120b:free",
        "gpt-oss-20b": "openrouter:openai/gpt-oss-20b:free",
        "gemma": "openrouter:google/gemma-4-31b-it:free",
        "gemma-26b": "openrouter:google/gemma-4-26b-a4b-it:free",
        "cohere": "openrouter:cohere/north-mini-code:free",
        "qwen-next": "openrouter:qwen/qwen3-next-80b-a3b-instruct:free",
        "qwen-coder": "openrouter:qwen/qwen3-coder:free",
        "lyria": "openrouter:google/lyria-3-pro-preview",
        "lyria-clip": "openrouter:google/lyria-3-clip-preview",
        "liquid": "openrouter:liquid/lfm-2.5-1.2b-thinking:free",
        "liquid-instruct": "openrouter:liquid/lfm-2.5-1.2b-instruct:free",
        "dolphin": "openrouter:cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "free": "openrouter:openrouter/free"
    }
    valid_local = ["auto", "flash", "pro"]
    
    if not args:
        current = user_models.get(chat_id, "auto")
        display_current = current.replace("openrouter:", "") if current.startswith("openrouter:") else current
        alias_list = " | ".join([f"`/model {k}`" for k in FREE_ALIASES.keys()])
        await update.message.reply_text(
            f"Current model: *{display_current}*\n\n"
            f"*Smart Routing:* `/model auto` (Auto-detects PII and routes to Free models or Private models)\n"
            f"*Private (G1) Models:* `/model flash` | `/model pro`\n"
            f"*Free OpenRouter Models:* {alias_list}\n\n"
            f"_(Note: OpenRouter endpoints are strictly hardcoded to the free tier to guarantee zero charges)_",
            parse_mode="Markdown"
        )
        return
        
    requested = args[0].lower()
    
    # 1. Map alias to full OpenRouter model
    is_safe_alias = False
    if requested in FREE_ALIASES:
        requested = FREE_ALIASES[requested]
        is_safe_alias = True
        
    # 2. Check validity and ENFORCE safety for manual entries
    if requested.startswith("openrouter:"):
        if not is_safe_alias and not requested.endswith(":free"):
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
    # sys.path already set at module level
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
    
    try:
        ai_result = await asyncio.to_thread(process_all_sources, canvas, classroom, gmail, groupme, announcements, docs)
    except Exception as e:
        logger.error(f"Error during AI digest generation: {e}")
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ The AI timed out or crashed while generating your digest: {e}")
        return
        
    # Ask user before pushing tasks to Notion
    import difflib
    state = load_state()
    new_tasks = []
    seen_titles = state.setdefault("seen_tasks", [])
    
    for task in ai_result.get("tasks", []):
        task_title = task.get("title", "").strip().lower()
        if not task_title: continue
        
        is_duplicate = False
        for seen in seen_titles:
            if difflib.SequenceMatcher(None, task_title, seen).ratio() > 0.8:
                is_duplicate = True
                break
                
        if not is_duplicate:
            new_tasks.append(task)
            seen_titles.append(task_title)
            
    state["seen_tasks"] = seen_titles
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
    if chat_id != config.SANEL_CHAT_ID:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized.")
        return

    cmd = " ".join(context.args)
    if not cmd:
        await context.bot.send_message(chat_id=chat_id, text="Usage: `/bash <command>`", parse_mode="Markdown")
        return

    msg = await context.bot.send_message(chat_id=chat_id, text=f"💻 Running: `{cmd}`...", parse_mode="Markdown")
    output = run_bash_safely(cmd, chat_id=chat_id)
    reply = "💻 **`" + cmd[:100] + "`**\n\n```\n" + output[:3800] + "\n```"
    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=reply, parse_mode="Markdown")
    except Exception:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=reply)

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
        async with message_lock:
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
            async with message_lock:
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
    from config import OR_FREE_MODELS
    
    try:
        extracted = call_openrouter(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            prompt=prompt,
            task="photo-extract",
            fallback_chain=["openrouter/owl-alpha"],
            timeout=120,
        )
    except Exception:
        logger.info("Falling back to G1 Flash for photo extraction...")
        from ai_processor import call_agy
        import asyncio
        extracted = await asyncio.to_thread(call_agy, prompt, 3600, "flash")

        if extracted and "NO_ALERT" not in extracted.upper() and "UNSURE" not in extracted.upper():
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload ---\n{extracted}\n")
            reply = f"✅ Important text found and saved for the next digest!\n\n_Filtered preview:_\n{extracted}"
            import glob
            history_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chat_history_{chat_id}_*.txt"))
            if history_files:
                latest_file = max(history_files, key=os.path.getmtime)
                with open(latest_file, "a") as f:
                    f.write(f"User: [I just uploaded a photo. Here is the raw text extracted from it: {ocr_text}]\nModel: (Image received. I am ready for questions about it.)\n\n")
        else:
            # User specifically sent a photo, so it's important regardless of what the small model thinks.
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
                f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
            reply = "⚠️ Local AI couldn't parse specific assignments, but I saved the raw text for the cloud AI to review!"
    except Exception as e:
        reply = f"❌ Local LLM connection error: {e}"
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "important_extracts.txt"), "a") as f:
            f.write(f"\n--- Photo Upload (Raw OCR) ---\n{ocr_text}\n")
            
        # Add to the most recently active chat history so the user can ask follow-up questions!
        import glob
        history_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chat_history_{chat_id}_*.txt"))
        if history_files:
            latest_file = max(history_files, key=os.path.getmtime)
            with open(latest_file, "a") as f:
                f.write(f"User: [I just uploaded a photo. Here is the raw text extracted from it: {ocr_text}]\nModel: (Image received. I am ready for questions about it.)\n\n")
        
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
    chat_id = query.message.chat_id

    # ── Quick action commands ────────────────────────────────────────────
    if data == "cmd:summary":
        context.args = []
        await summary_command(update, context)
        return
    elif data == "cmd:ping":
        await query.edit_message_text(get_health_status(), parse_mode="Markdown")
        return
    elif data == "cmd:stats":
        await query.edit_message_text(get_cost_summary(), parse_mode="Markdown")
        return
    elif data == "cmd:backup":
        path = create_backup()
        await query.edit_message_text(
            f"✅ Backup created: `{os.path.basename(path)}`" if path else "❌ Backup failed"
        )
        return
    elif data == "cmd:correlations":
        await query.edit_message_text(get_correlation_summary(), parse_mode="Markdown")
        return

    # ── Digest topic guide builder ───────────────────────────────────────
    if data.startswith("build_guide:"):
        topic = data.split("build_guide:", 1)[1]
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=query.message.message_id,
            text=f"� Building Mega Study Guide for: **{topic}**... This will take a minute!"
        )
        try:
            from scrapers.mega_study_builder import generate_mega_guide
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, generate_mega_guide, topic)
            try:
                await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=result)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to build guide: {e}")
        return
    elif data == "digest_dismiss":
        await query.edit_message_text("� Okay, I won't build a guide right now. Ask me anytime!")
        return

    # ── Task priority buttons ────────────────────────────────────────────
    if data.startswith("task_prio:"):
        parts = data.split(":")
        if len(parts) == 3:
            tid, prio = parts[1], parts[2]
            try:
                from notion_client import update_notion_task
                state = load_state()
                page_id = state.get("pending_priorities", {}).get(tid)
                if page_id and update_notion_task(page_id, priority=prio):
                    await query.edit_message_text(f"✅ Task `{tid}` priority set to **{prio}**")
                else:
                    await query.edit_message_text(f"❌ Could not update `{tid}`")
            except Exception as e:
                await query.edit_message_text(f"❌ Error: {e}")
        return
    elif data == "task_ignore_all":
        await query.edit_message_text("✅ All tasks ignored.")
        return

    # ── Photo response buttons ───────────────────────────────────────────
    if data == "photo:grade":
        await query.edit_message_text("� To grade a practice test, send a photo of your completed problems with the topic as a caption (e.g. 'SAT Math')")
        return
    elif data == "photo:save":
        await query.edit_message_text("✅ Got it — I'll save any photo text I see to your extracts.")
        return
    elif data == "photo:ask":
        await query.edit_message_text("💬 Ask me anything! Just reply to the photo text with your question.")
        return

    # ── Legacy: build_guide_ (drive file) ────────────────────────────────
    if data.startswith("build_guide_"):
        file_id = data.split("build_guide_")[1]
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=query.message.message_id,
            text="⏳ Downloading PDF, reading handwriting via Gemini Vision, and building Mega Study Guide... This will take a minute!"
        )
        loop = asyncio.get_event_loop()
        try:
            from scrapers.mega_study_builder import build_guide_for_drive_file
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
        
        # 4. Auto-Generate SAT Guides
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="💤 **Sleep Cycle:**\n✅ Web Pre-cached.\n4️⃣ Building Separated SAT Study Guides (Math, Reading, Writing)...", parse_mode="Markdown")
        except Exception: pass
        await asyncio.to_thread(subprocess.run, ['/home/sanel/personal-assistant-bot/venv/bin/python', '/home/sanel/personal-assistant-bot/run_builder.py', 'SAT Math and Geometry Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.to_thread(subprocess.run, ['/home/sanel/personal-assistant-bot/venv/bin/python', '/home/sanel/personal-assistant-bot/run_builder.py', 'SAT Reading Comprehension Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.to_thread(subprocess.run, ['/home/sanel/personal-assistant-bot/venv/bin/python', '/home/sanel/personal-assistant-bot/run_builder.py', 'SAT Writing and Grammar Master Guide'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
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
                    
        await asyncio.to_thread(subprocess.run, ['/home/sanel/personal-assistant-bot/venv/bin/python', '/home/sanel/personal-assistant-bot/run_builder.py', dynamic_topic], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"💤 **Sleep Cycle Complete:**\n✅ PDFs Processed\n✅ Memory Consolidated\n✅ Web Pre-cached\n✅ SAT Guide Updated\n✅ '{dynamic_topic}' Guide Generated!\n\nGood night! 🌙", parse_mode="Markdown")
        except Exception: pass
        
    except Exception as e:
        logger.error(f"Nightly sleep cycle error: {e}")

# ── NEW COMMAND HANDLERS ──────────────────────────────────────────────────────

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check: uptime, disk, last digest, queue size, file sizes."""
    await update.message.reply_text(get_health_status(), parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cost dashboard: LLM usage, tokens, estimated cost."""
    await update.message.reply_text(get_cost_summary(), parse_mode="Markdown")

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a backup now or list available backups."""
    msg = await update.message.reply_text("� Creating backup...")
    path = create_backup()
    if path:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, message_id=msg.message_id,
            text=f"✅ Backup created: `{os.path.basename(path)}`"
        )
    else:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, message_id=msg.message_id,
            text="❌ Backup failed. Check logs."
        )

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List or restore from backups. Usage: /restore [list|dry-run <path>]"""
    args = context.args
    if not args or args[0] == "list":
        backups = list_backups()
        if not backups:
            await update.message.reply_text("No backups found.")
            return
        lines = ["📦 **Available backups:**"]
        for b in backups:
            lines.append(f"  `{b['date']}` — {b['size_mb']}MB")
        lines.append("\nUse `/restore dry-run <path>` to preview restore.")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    elif args[0] == "dry-run" and len(args) > 1:
        result = restore_backup(args[1], dry_run=True)
        await update.message.reply_text(result, parse_mode="Markdown")

async def correlations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show cross-source correlation stats."""
    await update.message.reply_text(get_correlation_summary(), parse_mode="Markdown")


async def classroom_pdfs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download PDFs from Google Classroom assignments."""
    if update.effective_chat.id != SANEL_CHAT_ID:
        await update.message.reply_text("Unauthorized.")
        return

    msg = await update.message.reply_text("📥 Downloading Classroom PDFs...")
    try:
        from scrapers.google_scraper import download_classroom_pdfs
        result = download_classroom_pdfs("classroom_pdfs")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, message_id=msg.message_id,
            text=result
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, message_id=msg.message_id,
            text=f"❌ Error downloading PDFs: {e}"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands organized by category."""
    help_text = (
        "🤖 **Antigravity Bot Commands**\n\n"
        "**Core & Assistant**\n"
        "• `/help` - Show this menu\n"
        "• `/summary` - Manual data digest trigger\n"
        "• `/models` - List & switch AI models\n"
        "• `/bash <cmd>` - Run bash commands directly\n"
        "• `/p <num>` - Adjust bot priority queue\n\n"
        "**Server Management**\n"
        "• `/server` - Interactive Server Dashboard\n"
        "• `/ping` - Health check & uptime stats\n"
        "• `/stats` - Token & LLM cost usage dashboard\n\n"
        "**Data & Memory**\n"
        "• `/backup` - Create an immediate brain backup\n"
        "• `/restore` - List & restore backups\n"
        "• `/correlations` - Cross-source data correlation stats\n"
        "• `/classroom` - Download PDFs from Google Classroom"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def _get_server_overview():
    try:
        import subprocess
        res = subprocess.check_output("uptime", shell=True, text=True).strip()
        return f"🖥️ **Server Overview**\n`{res}`"
    except Exception as e: return str(e)

async def _get_mc_status():
    try:
        import subprocess
        res = subprocess.check_output("systemctl is-active minecraft || echo 'inactive'", shell=True, text=True).strip()
        return f"⛏️ **Minecraft Server**\nStatus: `{res}`"
    except Exception as e: return str(e)

async def _get_embed_status():
    try:
        import subprocess
        res = subprocess.check_output("tail -n 10 /tmp/embed_build4.log || echo 'No log found'", shell=True, text=True).strip()
        return f"🧠 **Embedding Progress**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _get_bot_status():
    try:
        import subprocess
        res = subprocess.check_output("systemctl status antigravity-bot | head -n 5", shell=True, text=True).strip()
        return f"🤖 **Bot Service**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _get_mc_log():
    try:
        import subprocess
        res = subprocess.check_output("journalctl -u minecraft -n 10 --no-pager", shell=True, text=True).strip()
        return f"📜 **MC Logs**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _get_ram_status():
    try:
        import subprocess
        res = subprocess.check_output("free -h", shell=True, text=True).strip()
        return f"💾 **RAM Usage**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _get_services_status():
    try:
        import subprocess
        res = subprocess.check_output("systemctl list-units --type=service --state=running | head -n 10", shell=True, text=True).strip()
        return f"⚙️ **Services**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _get_activity_feed():
    from activity_log import get_recent_events, format_events
    events = get_recent_events(10)
    return f"📈 **Activity Feed**\n{format_events(events)}"

async def _get_bot_log():
    try:
        import subprocess
        res = subprocess.check_output("journalctl -u antigravity-bot -n 10 --no-pager", shell=True, text=True).strip()
        return f"🤖 **Bot Logs**\n```\n{res}\n```"
    except Exception as e: return str(e)

async def _mc_start():
    try:
        import subprocess
        subprocess.check_output("sudo systemctl start minecraft", shell=True)
        return "✅ Minecraft server starting..."
    except Exception as e: return str(e)

async def _mc_stop():
    try:
        import subprocess
        subprocess.check_output("sudo systemctl stop minecraft", shell=True)
        return "🛑 Minecraft server stopping..."
    except Exception as e: return str(e)

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        help_txt = (
            "🎛️ **Server Dashboard**\n"
            "Usage: `/server <module>`\n\n"
            "Modules:\n"
            "• `overview` - Uptime & load\n"
            "• `ram` - Memory usage\n"
            "• `mc` - Minecraft status\n"
            "• `mcstart` / `mcstop` - Start/Stop MC\n"
            "• `mclog` - Minecraft latest logs\n"
            "• `bot` - Bot service status\n"
            "• `botlog` - Bot latest logs\n"
            "• `embed` - Embedding job status\n"
            "• `services` - Top running services\n"
            "• `activity` - Recent bot activity feed"
        )
        await update.message.reply_text(help_txt, parse_mode="Markdown")
        return
        
    cmd = args[0].lower()
    mapping = {
        "overview": _get_server_overview,
        "mc": _get_mc_status,
        "embed": _get_embed_status,
        "bot": _get_bot_status,
        "mclog": _get_mc_log,
        "ram": _get_ram_status,
        "services": _get_services_status,
        "activity": _get_activity_feed,
        "botlog": _get_bot_log,
        "mcstart": _mc_start,
        "mcstop": _mc_stop
    }
    
    if cmd in mapping:
        result = await mapping[cmd]()
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Unknown module: {cmd}")

# ── NEW: Import unified modules ───────────────────────────────────────────────
import config
from llm_router import call_openrouter, get_cost_summary, is_valid_response, OR_DEFAULT_MODEL, OR_FALLBACK_MODEL
from utils import (
    run_bash_safely, enforce_all_rotations, create_backup,
    get_health_status, get_correlation_summary, correlate_items,
    restore_backup, list_backups,
)
from inline_keyboards import (
    get_new_tasks_keyboard, get_digest_topic_keyboard,
    get_study_guide_keyboard, get_photo_response_keyboard,
    get_quick_actions_keyboard,
)
from voice_handler import transcribe_voice

# Track bot start time for /ping
BOT_START_TIME = time.time()

# ── Entry point ────────────────────────────────────────────────────────────────
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
        logger.warning(f"Initial context compile failed: {e}")
    
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

    # Graceful shutdown on SIGTERM (systemctl stop)
    import signal as _signal
    _shutdown_event = asyncio.Event()

    def _shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        _shutdown_event.set()

    _signal.signal(_signal.SIGTERM, _shutdown_handler)
    _signal.signal(_signal.SIGINT, _shutdown_handler)

    print("🤖 Antigravity Telegram bridge is running...")

    # Run with graceful shutdown
    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Bot stopped. Rotating files before exit...")
        enforce_all_rotations()

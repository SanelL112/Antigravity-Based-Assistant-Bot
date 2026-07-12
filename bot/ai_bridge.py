import os
import asyncio
import subprocess
import logging
import httpx
import time
from utils import scrub_pii, run_bash_safely
from activity_log import log_llm_call, log_event
from config import AGENTAPI_BIN, RESPONSE_TIMEOUT
from bot.state import load_state
from bot.runtime import _track_task

logger = logging.getLogger(__name__)

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
            asyncio.get_running_loop().run_in_executor(
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

    # ── PII CHECK: Fast regex scan before any cloud touch ──
    # If PII is detected, route the ENTIRE request to Orange Pi Ollama.
    # Primary: qwen2:0.5b (fast, ~53 tok/s)
    # Fallback: qwen2.5:3b-instruct-q4_K_M (capable, ~15 tok/s)
    # If both fail, fall through to cloud path with regex-scrubbed message.
    from utils import check_pii
    is_safe, scrubbed_message, pii_types = check_pii(user_message)

    if not is_safe:
        pii_str = ", ".join(pii_types)
        logger.info(f"PII detected ({pii_str}) — routing entirely via Pi Ollama")
        if status_msg and context:
            try: await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🛡️ PII detected ({pii_str}) — keeping it local on Pi")
            except Exception: pass

        from llm_router import call_ollama
        pi_prompt = (
            "You are a helpful, knowledgeable personal assistant. "
            "Keep your response concise and natural. Do not mention that you are an AI.\n\n"
            f"User: {scrubbed_message}"
        )
        pi_models = [
            ("qwen2:0.5b", "Pi 0.5B"),
            ("qwen2.5:3b-instruct-q4_K_M", "Pi 3.1B"),
        ]
        pi_result = ""
        for pi_model, pi_label in pi_models:
            try:
                pi_result = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda m=pi_model: call_ollama(pi_prompt, model=m, timeout=60)
                    ),
                    timeout=65,
                )
                if pi_result:
                    logger.info(f"{pi_label} responded: {len(pi_result)} chars")
                    return pi_result
                logger.warning(f"{pi_label} returned empty")
            except Exception as e:
                logger.warning(f"{pi_label} failed ({e})")

        logger.warning("All Pi models failed — falling through to cloud path with scrubbed data")
        # Replace original message with scrubbed version for the rest of this function
        user_message = scrubbed_message

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
        "- Server Status: Check system resources via bash [BASH]python3 -c 'import subprocess; print(subprocess.run([\"free\", \"-h\"], capture_output=True, text=True).stdout)'[/BASH]\n"
        "- Embedding Progress: Check the offline indexer via bash [BASH]python3 -c 'import os; print(open(\"/tmp/embed_build4.log\").read()[-500:] if os.path.exists(\"/tmp/embed_build4.log\") else \"No log found\")'[/BASH]\n"
        "- Minecraft Server: Check MC via bash [BASH]python3 -c 'import asyncio; from bot.commands import _get_mc_status; print(asyncio.run(_get_mc_status()))'[/BASH], start [BASH]python3 -c 'import asyncio; from bot.commands import _mc_start; print(asyncio.run(_mc_start()))'[/BASH], stop [BASH]python3 -c 'import asyncio; from bot.commands import _mc_stop; print(asyncio.run(_mc_stop()))'[/BASH]\n"
        "- Activity Log: Check recent bot events via bash [BASH]python3 -c 'from activity_log import get_recent_events, format_events; print(format_events(get_recent_events(10)))'[/BASH]\n\n"
        "--- ACADEMIC & STUDY ---\n"
        "- STUDY COMPANION: If Sanel asks you to build a study guide, find a YouTube video for a topic, or research something to study, you MUST use the mega study builder script via bash:\n"
        "[BASH]python3 -c 'from scrapers.mega_study_builder import generate_mega_guide; print(generate_mega_guide(\"Topic Name Here\"))'[/BASH]\n"
        "- DEEP-DIVE KNOWLEDGE BASE: An offline researcher runs every night to compile massive study sheets on your current topics. If Sanel asks a question about an academic topic, check if a guide exists by using bash to list and read files in `/home/sanel/personal-assistant-bot/knowledge_base/` before answering, so you can interact and research much faster!\n"
        "- KNOWLEDGE GAP TRACKING: If you are grading an answer or helping Sanel with a problem and you notice a weakness (e.g. \"struggles with polynomial factoring\"), you MUST log this to a text file using python: [BASH]python3 -c 'with open(\"/home/sanel/personal-assistant-bot/knowledge_gaps/math.txt\", \"a\") as f: f.write(\"Struggles with factoring when a > 1\\n\")'[/BASH] so the offline researcher can heavily target his weak points tonight.\n\n"
        "--- LIFE MANAGEMENT ---\n"
        "- Every 4 hours: auto-digest from Canvas, Classroom, Gmail, GroupMe\n"
        "- Notion: assignments auto-pushed to Tasks Tracker\n"
        "- Natural Language Notion Pushes: When the background job alerts Sanel about a NEW task and asks him for priority/status, you MUST push it to Notion using the add_task_to_notion python script when he replies! Example:\n"
        "[BASH]python3 -c 'from scrapers.notion_client import add_task_to_notion; add_task_to_notion(title=\"Math Homework\", priority=\"high\", status=\"Not started\", start_value=0, end_value=100)'[/BASH]\n"
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
    
    state = load_state()
    model = state["user_models"].get(str(chat_id), "auto")
    
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
                asyncio.get_running_loop().run_in_executor(
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
                                                        from utils import sanitize_markdown
                                                        safe_disp = sanitize_markdown(disp)
                                                        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 **Thinking...**\n_{safe_disp}_", parse_mode="Markdown")
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

            # ── OpenRouter fallback chain: try OR models in order ──
            or_fallback_models = []
            if or_model_name == "nvidia/nemotron-3-ultra-550b-a55b:free":
                from config import OR_FALLBACK_MODEL, OR_THIRD_MODEL
                or_fallback_models = [OR_FALLBACK_MODEL, OR_THIRD_MODEL]

            # Check if primary model failed or refused
            if not out or (isinstance(out, str) and any(p in out.lower()[:50] for p in fail_phrases)):
                fallback_tried = False
                for fb_model in or_fallback_models:
                    logger.warning(f"{or_model_name} failed. Falling back to {fb_model}...")
                    try:
                        if status_msg and context:
                            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 Generating response using {fb_model}...")
                        fb_out = await _call_or(fb_model)
                        if fb_out and not any(p in fb_out.lower()[:50] for p in fail_phrases):
                            out = fb_out
                            actual_model_used = fb_model
                            fallback_tried = True
                            break
                    except Exception:
                        continue

                if not fallback_tried:
                    # ── Cross-provider: try Opencode Zen (separate rate limit bucket) ──
                    logger.warning("OpenRouter models all failed. Trying Opencode Zen (hy3-free)...")
                    try:
                        from llm_router import call_opencode
                        zen_out = await asyncio.get_running_loop().run_in_executor(
                            None,
                            lambda: call_opencode("hy3-free", full_prompt, task=f"chat-{topic}", timeout=RESPONSE_TIMEOUT)
                        )
                        if zen_out:
                            out = zen_out
                            actual_model_used = "hy3-free (Opencode Zen)"
                        else:
                            raise Exception("empty")
                    except Exception as ze:
                        logger.warning(f"Opencode Zen also failed ({ze}). Trying Hack Club AI...")
                        try:
                            from llm_router import call_hackclub
                            hc_out = await asyncio.get_running_loop().run_in_executor(
                                None,
                                lambda: call_hackclub("qwen/qwen3-32b", full_prompt, task=f"chat-{topic}", timeout=RESPONSE_TIMEOUT)
                            )
                            if hc_out:
                                out = hc_out
                                actual_model_used = "qwen3-32b (Hack Club AI)"
                            else:
                                raise Exception("empty")
                        except Exception as he:
                            logger.warning(f"Hack Club AI also failed ({he}). Falling back to local G1 Flash...")
                            try:
                                result = await asyncio.wait_for(
                                    asyncio.get_running_loop().run_in_executor(
                                        None,
                                        lambda: subprocess.run([AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", full_prompt], capture_output=True, text=True, timeout=RESPONSE_TIMEOUT, stdin=subprocess.DEVNULL)
                                    ), timeout=RESPONSE_TIMEOUT + 5)
                                out = result.stdout.strip()
                                actual_model_used = "flash (local fallback)"
                            except Exception as e3:
                                out = f"⚠️ Fallback to G1 Exception: {e3}"
        except Exception as e:
            if or_model_name == "nvidia/nemotron-3-ultra-550b-a55b:free":
                from config import OR_FALLBACK_MODEL, OR_THIRD_MODEL
                logger.warning(f"Primary model exception ({e}). Trying fallback chain...")
                fallback_tried = False
                for fb_model in [OR_FALLBACK_MODEL, OR_THIRD_MODEL]:
                    try:
                        if status_msg and context:
                            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"🧠 Trying {fb_model}...")
                        fb_out = await _call_or(fb_model)
                        if fb_out:
                            out = fb_out
                            actual_model_used = fb_model
                            fallback_tried = True
                            break
                        else:
                            raise Exception(f"{fb_model} empty")
                    except Exception:
                        continue

                if not fallback_tried:
                    # ── Cross-provider: Opencode Zen ──
                    logger.warning("All streaming OpenRouter models failed. Trying Opencode Zen...")
                    try:
                        from llm_router import call_opencode
                        zen_out = await asyncio.get_running_loop().run_in_executor(
                            None,
                            lambda: call_opencode("hy3-free", full_prompt, task=f"chat-{topic}", timeout=RESPONSE_TIMEOUT)
                        )
                        if zen_out:
                            out = zen_out
                            actual_model_used = "hy3-free (Opencode Zen)"
                        else:
                            raise Exception("empty")
                    except Exception as ze:
                        logger.warning(f"Opencode Zen also failed ({ze}). Trying Hack Club AI...")
                        try:
                            from llm_router import call_hackclub
                            hc_out = await asyncio.get_running_loop().run_in_executor(
                                None,
                                lambda: call_hackclub("qwen/qwen3-32b", full_prompt, task=f"chat-{topic}", timeout=RESPONSE_TIMEOUT)
                            )
                            if hc_out:
                                out = hc_out
                                actual_model_used = "qwen3-32b (Hack Club AI)"
                            else:
                                raise Exception("empty")
                        except Exception as he:
                            logger.warning(f"Hack Club AI also failed ({he}). Falling back to local G1 Flash...")
                            try:
                                result = await asyncio.wait_for(
                                    asyncio.get_running_loop().run_in_executor(
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
                asyncio.get_running_loop().run_in_executor(
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
                    asyncio.get_running_loop().run_in_executor(
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
                            asyncio.get_running_loop().run_in_executor(
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
                    asyncio.get_running_loop().run_in_executor(
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
                    from utils import sanitize_markdown
                    safe_summary = sanitize_markdown(summary_text)
                    await context.bot.send_message(chat_id=chat_id_to_notify, text=f"🤖 **Verification ({OR_FALLBACK_MODEL}):**\n{safe_summary}", parse_mode="Markdown")
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

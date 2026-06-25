"""
ai_processor.py - Runs one agy prompt per source, saves results to text files,
then assembles the final digest and task list from those files.
"""

import json
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BOT_DIR, "source_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ── Per-source prompts ────────────────────────────────────────────────────────

SOURCE_PROMPTS = {
    "canvas": (
        "Read the raw data below. Does it contain ANY upcoming assignments, deadlines, announcements, or anything else that might be useful?\n"
        "If you are 100% sure it is empty or useless, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if it contains ANY data, reply exactly with: IMPORTANT\n\n"
        "Raw Canvas data:\n{data}"
    ),
    "classroom": (
        "Read the raw data below. Does it contain ANY assignments, homework, or classwork?\n"
        "If you are 100% sure it is empty or useless, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if it contains ANY data, reply exactly with: IMPORTANT\n\n"
        "Raw Classroom data:\n{data}"
    ),
    "gmail": (
        "Read the raw data below. Does it contain ANY emails from real people, teachers, or important senders?\n"
        "If you are 100% sure they are ALL spam or marketing, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if there is ANY real email, reply exactly with: IMPORTANT\n\n"
        "Raw Gmail data:\n{data}"
    ),
    "groupme": (
        "Read the raw data below. Does it contain ANY new events, announcements, or conversations?\n"
        "If you are 100% sure it is empty or useless, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if it contains ANY data, reply exactly with: IMPORTANT\n\n"
        "Raw GroupMe data:\n{data}"
    ),
    "classroom_announcements": (
        "Read the raw data below. Does it contain ANY announcements or class posts?\n"
        "If you are 100% sure it is empty or useless, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if it contains ANY data, reply exactly with: IMPORTANT\n\n"
        "Raw Classroom Announcements:\n{data}"
    ),
    "gdocs": (
        "Read the raw Google Docs data below. Does it contain ANY notes, homework, or text?\n"
        "If you are 100% sure it is completely empty or useless, reply exactly with: NO_IMPORTANT_UPDATES\n"
        "Otherwise, if it contains ANY data, reply exactly with: IMPORTANT\n\n"
        "Raw Docs Text:\n{data}"
    ),
}

DIGEST_ASSEMBLY_PROMPT = (
    "You are Sanel Lathiya's personal assistant bot. "
    "Below are pre-processed summaries from each data source. "
    "Assemble them into ONE beautifully formatted Markdown digest message to send via Telegram.\n\n"
    "Rules:\n"
    "- Use emoji section headers: 📚 Canvas, 🏫 Google Classroom, 📢 Classroom Announcements, 📧 Gmail, 💬 GroupMe\n"
    "- Keep each section concise. Skip sections that say 'No urgent updates'.\n"
    "- End with a friendly one-liner.\n"
    "- Return ONLY the Markdown text, no JSON, no explanation.\n\n"
    "Summaries:\n{summaries}\n\n"
    "At the very end, return two JSON objects on their own lines:\n"
    "1. A JSON list of specific upcoming subjects/topics the user has tests, quizzes, or heavy assignments for, in this exact format:\n"
    "STUDY_TOPICS_JSON:[\"Calculus Limits\", \"Photosynthesis\"]\n"
    "2. A JSON list of tasks in this exact format:\n"
    "TASKS_JSON:[{{\"id\":\"...\",\"title\":\"...\",\"source\":\"...\",\"due_date\":null,\"priority\":\"medium\",\"status\":\"Not started\",\"start_value\":0,\"end_value\":100}}]\n"
    "CRITICAL: If you cannot confidently determine the 'priority', 'status', 'start_value', or 'end_value' from the text, set that specific field to 'unknown'."
)

# ── agy helper ────────────────────────────────────────────────────────────────

def call_agy(prompt: str, timeout: int = 180, model: str = "flash") -> str:
    """Call agy --print using a PTY. Attempts 'flash' first, then falls back to 'pro'."""
    import pty, select, time, os as _os
    
    def _run_model(target_model: str) -> str:
        master = -1
        proc = None
        try:
            master, slave = pty.openpty()
            proc = subprocess.Popen(
                [AGENTAPI_BIN, "--model", target_model, "--print", prompt],
                stdin=slave, stdout=slave, stderr=slave,
                close_fds=True
            )
            _os.close(slave)

            output_chunks = []
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    r, _, _ = select.select([master], [], [], 1.0)
                    if r:
                        try:
                            chunk = _os.read(master, 4096)
                            output_chunks.append(chunk)
                        except OSError:
                            break
                except Exception:
                    break
                if proc.poll() is not None:
                    try:
                        while True:
                            r, _, _ = select.select([master], [], [], 0.2)
                            if r:
                                chunk = _os.read(master, 4096)
                                output_chunks.append(chunk)
                            else:
                                break
                    except OSError:
                        pass
                    break

            try:
                proc.wait(timeout=5)
            except Exception:
                pass

            raw = b"".join(output_chunks).decode("utf-8", errors="replace")
            import re
            clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', raw)
            clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()
            
            if proc.poll() is None:
                # Process timed out
                logger.error(f"agy {target_model} timed out after {timeout}s")
                try:
                    proc.kill()
                except Exception:
                    pass
                return ""
                
            return clean

        except Exception as e:
            logger.error(f"agy pty error ({target_model}): {e}")
            return ""
        finally:
            # Always close master FD to prevent file descriptor leak
            if master >= 0:
                try:
                    _os.close(master)
                except OSError:
                    pass
            # Ensure process is cleaned up
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    logger.info(f"Attempting processing with {model}...")
    result = _run_model(model)
    if not result and model != "pro":
        logger.warning(f"{model} failed or timed out. Falling back to pro...")
        result = _run_model("pro")
        
    return result

def call_local_llm(prompt: str) -> str:
    """Calls Qwen2 0.5B via Ollama. Falls back to Llama 3.2 3B if unsure."""
    import requests
    import json
    
    def _call(model_name: str) -> str:
        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                },
                timeout=60
            )
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                logger.error(f"Ollama returned {res.status_code} for {model_name}")
                return ""
        except Exception as e:
            logger.error(f"Ollama connection error for {model_name}: {e}")
            return ""

    response = _call("hf.co/Qwen/Qwen2-0.5B-Instruct-GGUF:latest")
    
    if "UNSURE" in response.upper():
        logger.info("Qwen2:0.5b was UNSURE. Falling back to Llama 3.2 3B GGUF...")
        response = _call("hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest")
        
    return response if response else "Could not summarize locally."



# ── Per-source processing ─────────────────────────────────────────────────────

def process_source(name: str, data: str, skip_llm_filter: bool = False) -> str:
    """Run agy for a single source. Saves result to cache file. Returns summary text."""
    cache_file = os.path.join(CACHE_DIR, f"{name}_summary.txt")

    if not data or data.strip() == "" or "not configured" in data.lower():
        summary = f"No {name} data available."
        with open(cache_file, "w") as f:
            f.write(summary)
        return summary

    if skip_llm_filter:
        logger.info(f"Bypassing LOCAL Qwen2 0.5B for high-signal source {name} — passing full raw data ({len(data)} chars).")
        summary = data
    else:
        # Cap the data sent to Qwen at 4000 chars for classification only.
        # The full raw data is still passed to agy if marked IMPORTANT.
        classification_data = data[:4000] + ("\n[...trimmed for classification...]" if len(data) > 4000 else "")
        prompt = SOURCE_PROMPTS[name].format(data=classification_data)
        
        # Inject user's dynamic learning rules
        rules_file = os.path.join(BOT_DIR, "learning_rules.txt")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r") as f:
                    rules = f.read().strip()
                if rules:
                    prompt += f"\n\nUSER'S CUSTOM RULES (MUST FOLLOW):\n{rules}\n"
            except Exception:
                pass
                
        # Inject the fallback and learning triggers
        prompt += "\n\nCRITICAL RULE 1: If you are unsure if there is anything important, or you cannot understand the text, you MUST reply exactly with the word: UNSURE"
        prompt += "\nCRITICAL RULE 2: If you see a completely new type of message, sender, or topic that you are not sure is important (and it's not in the custom rules), you MUST reply exactly in this format: [ASK_USER] Brief description of the new item."
        
        logger.info(f"Calling LOCAL Qwen2 0.5B for {name} ({len(prompt)} chars)...")

        response = call_local_llm(prompt)
        if not response or "UNSURE" in response.upper():
            logger.info(f"Qwen2 returned empty or UNSURE for {name} — passing full raw data ({len(data)} chars) to agy.")
            summary = data # Fallback to passing raw data to agy
        elif "NO_IMPORTANT_UPDATES" in response.upper():
            summary = f"No urgent {name} updates."
        elif "[ASK_USER]" in response.upper():
            summary = f"{response}\n\nRAW DATA:\n{data}"
        else:
            # It is IMPORTANT! Pass raw data to agy.
            summary = data

    with open(cache_file, "w") as f:
        f.write(summary)
    logger.info(f"Saved {name} summary to {cache_file}")
    return summary


# ── Final assembly ────────────────────────────────────────────────────────────

def assemble_digest(summaries: dict) -> dict:
    """Assemble per-source summaries into a final digest + task list via agy."""
    summary_text = ""
    for name, text in summaries.items():
        summary_text += f"=== {name.upper()} ===\n{text}\n\n"

    # Save combined summaries to file for reference (APPEND so memory consolidation can read the whole day)
    with open(os.path.join(CACHE_DIR, "combined_summaries.txt"), "a") as f:
        f.write(summary_text)
        
    # Read and inject local OCR / photo extracts
    extracts_file = os.path.join(BOT_DIR, "important_extracts.txt")
    if os.path.exists(extracts_file):
        try:
            with open(extracts_file, "r") as f:
                extracts = f.read().strip()
            if extracts:
                summary_text += f"\n=== LOCAL PHOTO / OFFLINE EXTRACTS ===\n{extracts}\n\n"
            # Clear the file now that it's in the digest
            with open(extracts_file, "w") as f:
                f.write("")
        except Exception as e:
            logger.error(f"Failed to read extracts: {e}")

    prompt = DIGEST_ASSEMBLY_PROMPT.format(summaries=summary_text)
    logger.info("Assembling final digest via agy...")
    output = call_agy(prompt, timeout=3600)

    if not output:
        return {"tasks": [], "digest": "", "topics": []}

    # Split tasks JSON and topics JSON from the digest text
    tasks = []
    topics = []
    digest = output
    
    import re as _re
    tasks_match = _re.search(r'TASKS_JSON:(.*?)(?:STUDY_TOPICS_JSON:|$)', digest, _re.DOTALL)
    if tasks_match:
        try:
            tasks = json.loads(tasks_match.group(1).strip())
        except Exception:
            pass
        digest = digest.replace('TASKS_JSON:' + tasks_match.group(1), '').strip()

    topics_match = _re.search(r'STUDY_TOPICS_JSON:(.*?)(?:TASKS_JSON:|$)', digest, _re.DOTALL)
    if topics_match:
        try:
            topics = json.loads(topics_match.group(1).strip().split('\n')[0])
        except Exception:
            pass
        digest = digest.replace('STUDY_TOPICS_JSON:' + topics_match.group(1).split('\n')[0], '').strip()

    # ── Deduplication: compare with previous digest via agy Flash ────────────
    previous_digest_path = os.path.join(BOT_DIR, "latest_digest.txt")
    previous_digest = ""
    try:
        with open(previous_digest_path, "r") as f:
            previous_digest = f.read().strip()
    except Exception:
        pass

    if previous_digest:
        dedup_prompt = (
            "You are a digest deduplication assistant.\n"
            "Below is a PREVIOUS digest and a NEW digest.\n"
            "Your job is to return the NEW digest with any bullet points, items, or sections "
            "that are IDENTICAL or essentially the same as the previous digest REMOVED.\n"
            "Keep everything that is genuinely new, changed, or updated.\n"
            "If everything is new, return the full new digest unchanged.\n"
            "If nothing is new, return exactly: NO_NEW_UPDATES\n"
            "Return ONLY the final cleaned digest text, no explanation.\n\n"
            f"--- PREVIOUS DIGEST ---\n{previous_digest}\n\n"
            f"--- NEW DIGEST ---\n{digest}"
        )
        logger.info("Deduplicating digest via agy Flash...")
        deduped = call_agy(dedup_prompt, timeout=60, model="flash")
        if deduped and deduped.strip() != "NO_NEW_UPDATES" and len(deduped.strip()) > 20:
            digest = deduped.strip()
            logger.info("Deduplication complete — new content only.")
        elif deduped.strip() == "NO_NEW_UPDATES":
            digest = "✅ Nothing new since the last digest — all caught up!"
            logger.info("Deduplication: no new updates found.")
        else:
            logger.warning("Deduplication failed or returned empty — using full digest.")

    # Save final digest to file
    with open(previous_digest_path, "w") as f:
        f.write(digest)

    return {"tasks": tasks, "digest": digest, "topics": topics}


# ── Main entry point ──────────────────────────────────────────────────────────

def process_all_sources(canvas_data: str, classroom_data: str, gmail_data: str, groupme_data: str, classroom_ann_data: str = "No recent announcements.", gdocs_data: str = "No recent docs.") -> dict:
    """Passes all raw data through the AI pipeline."""
    
    # 1. Summarize each source (could run in parallel, but sequential is fine for now)
    logger.info("Summarizing Canvas...")
    canvas_summary = process_source("canvas", canvas_data, skip_llm_filter=True)
    
    logger.info("Summarizing Google Classroom Assignments...")
    classroom_summary = process_source("classroom", classroom_data, skip_llm_filter=True)
    
    logger.info("Summarizing Google Classroom Announcements...")
    classroom_ann_summary = process_source("classroom_announcements", classroom_ann_data, skip_llm_filter=True)
    
    logger.info("Summarizing Gmail...")
    gmail_summary = process_source("gmail", gmail_data, skip_llm_filter=False)
    
    logger.info("Summarizing GroupMe...")
    groupme_summary = process_source("groupme", groupme_data, skip_llm_filter=False)
    
    logger.info("Summarizing Google Docs...")
    gdocs_summary = process_source("gdocs", gdocs_data, skip_llm_filter=True)
    
    # 2. Combine all summaries into one assembly block
    summaries = {
        "canvas": canvas_summary,
        "classroom": classroom_summary,
        "classroom_announcements": classroom_ann_summary,
        "gmail": gmail_summary,
        "groupme": groupme_summary,
        "gdocs": gdocs_summary,
    }
    
    return assemble_digest(summaries)

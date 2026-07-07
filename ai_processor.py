"""
ai_processor.py - Runs one agy prompt per source, saves results to text files,
then assembles the final digest and task list from those files.

REFACTORED: Uses llm_router for unified OpenRouter calls and llm_cost_log for tracking.
Local agy/Ollama calls remain for PII-safe processing.
"""

import json
import subprocess
import os
import logging
import threading
from pathlib import Path
logging.basicConfig(level=logging.INFO, format='%(message)s')

logger = logging.getLogger(__name__)

# Use unified config
from config import AGENTAPI_BIN, BASE_DIR, CACHE_DIR as CONFIG_CACHE_DIR, LATEST_DIGEST_FILE
BOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = Path(CONFIG_CACHE_DIR)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
_write_lock = threading.Lock()

# ── Per-source prompts ────────────────────────────────────────────────────────


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
    """
    Call agy --print using a PTY. Attempts 'flash' first, then falls back to 'pro'.

    DELEGATES to llm_router.call_agy_local() — the unified implementation.
    This wrapper preserves the original function signature for backward compatibility.
    """
    try:
        from llm_router import call_agy_local
        return call_agy_local(prompt=prompt, model=model, timeout=timeout)
    except ImportError:
        # Fallback: PTY implementation if llm_router not available
        return _call_agy_inline(prompt, timeout, model)


def _call_agy_inline(prompt: str, timeout: int = 180, model: str = "flash") -> str:
    """Original inline PTY implementation (kept as fallback)."""
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
            if master >= 0:
                try:
                    _os.close(master)
                except OSError:
                    pass
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
    """
    Calls Qwen2 0.5B via Ollama. Falls back to Llama 3.2 3B if unsure.
    Delegates to llm_router for unified Ollama calls.
    """
    try:
        from llm_router import call_ollama
        response = call_ollama(prompt, model="hf.co/Qwen/Qwen2-0.5B-Instruct-GGUF:latest")
        if "UNSURE" in response.upper():
            logger.info("Qwen2:0.5b was UNSURE. Falling back to Llama 3.2 3B GGUF...")
            response = call_ollama(prompt, model="hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest")
        return response if response else "Could not summarize locally."
    except ImportError:
        pass

    # Fallback: inline implementation
    import requests
    def _call(model_name: str) -> str:
        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
                timeout=60
            )
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            return ""
        except Exception as e:
            logger.error(f"Ollama error for {model_name}: {e}")
            return ""

    response = _call("hf.co/Qwen/Qwen2-0.5B-Instruct-GGUF:latest")
    if "UNSURE" in response.upper():
        response = _call("hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest")
    return response if response else "Could not summarize locally."



# ── Per-source processing ─────────────────────────────────────────────────────

def process_source(name: str, data: str, skip_llm_filter: bool = False, force_reprocess: bool = False) -> str:
    """Run agy for a single source. Saves result to cache file. Returns summary text."""
    cache_file = os.path.join(CACHE_DIR, f"{name}_summary.txt")

    if not data or data.strip() == "" or "not configured" in data.lower():
        summary = f"No {name} data available."
        with open(cache_file, "w") as f:
            f.write(summary)
        return summary

    # Content-hash caching: skip LLM processing if source unchanged
    if not force_reprocess:
        try:
            from utils import has_changed, mark_processed
            if not has_changed(name, data[:1000]):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached = f.read()
                    if cached and cached != f"No {name} data available.":
                        logger.info(f"Source {name} unchanged — using cached summary ({len(cached)} chars)")
                        return cached
                except Exception:
                    pass  # cache miss, process normally
        except ImportError:
            pass  # utils not available, skip caching

    if skip_llm_filter:
        logger.info(f"Bypassing classification for high-signal source {name} — passing full raw data ({len(data)} chars).")
        summary = data
    else:
        # Lightweight classification via agy flash (replaces old Qwen2 0.5B → Llama → agy 3-step chain)
        prompt = (
            f"Read the following {name} data. If it contains ANY useful info, summarize it concisely. "
            f"If it's empty/useless, reply exactly: NO_IMPORTANT_UPDATES\n\n"
            f"DATA:\n{data[:8000]}"
        )

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

        prompt += "\n\nIf you see a completely new type of item you're unsure about, reply: [ASK_USER] description"

        logger.info(f"Calling agy flash for {name} classification ({len(prompt)} chars)...")
        response = call_agy(prompt, timeout=60, model="flash")

        if not response or "NO_IMPORTANT_UPDATES" in response.upper():
            summary = f"No urgent {name} updates."
        elif "[ASK_USER]" in response:
            summary = f"{response}\n\nRAW DATA:\n{data}"
        else:
            summary = response

    with open(cache_file, "w") as f:
        f.write(summary)
        
    try:
        from utils import mark_processed
        mark_processed(name, data[:1000])
    except ImportError:
        pass
        
    logger.info(f"Saved {name} summary to {cache_file}")
    return summary


# ── Final assembly ────────────────────────────────────────────────────────────

def assemble_digest(summaries: dict) -> dict:
    """Assemble per-source summaries into a final digest + task list via agy."""
    summary_text = ""
    for name, text in summaries.items():
        summary_text += f"=== {name.upper()} ===\n{text}\n\n"

    # Save combined summaries to file for reference (APPEND so memory consolidation can read the whole day)
    # Use atomic append with lock to prevent interleaved writes from ThreadPoolExecutor
    combined_summaries_path = os.path.join(CACHE_DIR, "combined_summaries.txt")
    with _write_lock:
        with open(combined_summaries_path, "a", encoding="utf-8") as f:
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

    # ── Deduplication: bullet-level string comparison (fast, no LLM) ─────────
    previous_digest_path = LATEST_DIGEST_FILE
    previous_digest = ""
    try:
        with open(previous_digest_path, "r", encoding="utf-8") as f:
            previous_digest = f.read().strip()
    except Exception:
        pass

    if previous_digest:
        import re as _re

        # Extract normalized bullet lines from previous digest
        prev_bullets = set()
        for line in previous_digest.split("\n"):
            line = line.strip()
            if line.startswith(("•", "-", "✅", "📎", "▶️")):
                normalized = _re.sub(r'[^\w\s]', '', line).strip().lower()
                prev_bullets.add(normalized)

        kept = []
        new_bullet_count = 0
        for line in digest.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("•", "-", "✅", "�", "▶️")):
                normalized = _re.sub(r'[^\w\s]', '', stripped).strip().lower()
                if normalized not in prev_bullets:
                    kept.append(line)
                    new_bullet_count += 1
                # else: duplicate bullet, skip
            else:
                kept.append(line)  # keep headers, blank lines, etc.

        if new_bullet_count == 0:
            digest = "✅ Nothing new since the last digest — all caught up!"
            logger.info("Deduplication: no new updates found (bullet-level).")
        else:
            digest = "\n".join(kept)
            logger.info(f"Deduplication: kept {new_bullet_count} new bullets, removed duplicates.")

    # Save final digest to file
    with open(previous_digest_path, "w") as f:
        f.write(digest)

    return {"tasks": tasks, "digest": digest, "topics": topics}


# ── Main entry point ──────────────────────────────────────────────────────────

def process_all_sources(canvas_data: str, classroom_data: str, gmail_data: str, groupme_data: str, classroom_ann_data: str = "No recent announcements.", gdocs_data: str = "No recent docs.") -> dict:
    """Passes all raw data through the AI pipeline. Runs sources in parallel."""

    # 1. Summarize all 6 sources in parallel (independent I/O-bound work)
    import concurrent.futures
    sources = [
        ("canvas", canvas_data, True, False),
        ("classroom", classroom_data, True, False),
        ("classroom_announcements", classroom_ann_data, True, False),
        ("gmail", gmail_data, False, False),
        ("groupme", groupme_data, False, False),
        ("gdocs", gdocs_data, True, False),
    ]

    def _process_one(args):
        name, data, skip, force = args
        logger.info(f"Summarizing {name}...")
        return name, process_source(name, data, skip_llm_filter=skip, force_reprocess=force)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for name, summary in pool.map(_process_one, sources):
            results[name] = summary

    # 2. Combine all summaries into one assembly block
    summaries = {
        "canvas": results["canvas"],
        "classroom": results["classroom"],
        "classroom_announcements": results["classroom_announcements"],
        "gmail": results["gmail"],
        "groupme": results["groupme"],
        "gdocs": results["gdocs"],
    }

    return assemble_digest(summaries)

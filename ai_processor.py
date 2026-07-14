"""
ai_processor.py - Runs one agy prompt per source, saves results to text files,
then assembles the final digest and task list from those files.

REFACTORED: Uses llm_router for unified OpenRouter calls and llm_cost_log for tracking.
Local agy/Ollama calls remain for PII-safe processing.
"""

import asyncio
import json
import logging
import os
import subprocess
import threading
from pathlib import Path

try:
    import aiohttp
except ImportError:
    aiohttp = None  # optional: only needed for Pi classifier
logging.basicConfig(level=logging.INFO, format='%(message)s')

logger = logging.getLogger(__name__)

# Use unified config
from config import AGENTAPI_BIN, CACHE_DIR as CONFIG_CACHE_DIR, LATEST_DIGEST_FILE
BOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = Path(CONFIG_CACHE_DIR)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Module-level lock for thread-safe file writes (shared across ThreadPoolExecutor workers)
_write_lock = threading.Lock()

# ── Orange Pi 5 Classifier Integration ────────────────────────────────────────
# Offloads batch classification to the Pi's 8 cores (qwen2:0.5b, 4 concurrent
# workers) so the main server stays free for heavier inference.

PI_CLASSIFIER_URL = "http://10.10.10.2:8080"


async def pi_classify_batch(items: list[dict]) -> list[dict] | None:
    """
    Send batch classification to Orange Pi 5 pipeline.

    Each item: {"id": str, "source": str, "text": str}
    Returns: list of classification results, or None if Pi is unreachable.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=60, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{PI_CLASSIFIER_URL}/classify",
                json=items,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"Pi classifier returned HTTP {resp.status}")
                return None
    except Exception as e:
        logger.info(f"Pi classifier unavailable (falling back to local): {e}")
        return None


def pi_classify_sync(items: list[dict]) -> list[dict] | None:
    """Synchronous wrapper for ThreadPoolExecutor."""
    try:
        return asyncio.run(pi_classify_batch(items))
    except Exception as e:
        logger.warning(f"Pi classifier sync call failed: {e}")
        return None


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
                except Exception as e:
                    logger.debug("PTY select error during pty poll: %r", e)
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
            except Exception as e:
                logger.debug("proc.wait error: %r", e)

            raw = b"".join(output_chunks).decode("utf-8", errors="replace")
            import re
            clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', raw)
            clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()
            
            if proc.poll() is None:
                logger.error(f"agy {target_model} timed out after {timeout}s")
                try:
                    proc.kill()
                except Exception as e:
                    logger.debug("proc.kill error after wait timeout: %r", e)
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
                except Exception as e:
                    logger.debug("proc.kill error in finally: %r", e)

    logger.info(f"Attempting processing with {model}...")
    result = _run_model(model)
    if not result and model != "pro":
        logger.warning(f"{model} failed or timed out. Falling back to pro...")
        result = _run_model("pro")
        
    return result

# NOTE: call_local_llm was removed — no callers remain (verified via repo-wide grep).
# Superseded by the Pi classifier pre-filter + agy flash pipeline in process_source().
# The original Qwen2 0.5B -> Llama 3.2 3B fallback chain is still visible in git history
# (git log -- ai_processor.py), last present in d7c2c92.



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
            from utils import has_changed
            if not has_changed(name, data[:1000]):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached = f.read()
                    if cached and cached != f"No {name} data available.":
                        logger.info(f"Source {name} unchanged — using cached summary ({len(cached)} chars)")
                        return cached
                except Exception as e:
                    logger.debug(f"cache read fell through, regenerating {name}: %r", e)
        except ImportError:
            pass  # utils not available, skip caching

    # ── Stage 1: Try Orange Pi 5 classifier first (fast, saves agy credits) ──
    if not skip_llm_filter:
        pi_result = pi_classify_sync([{"id": "1", "source": name, "text": data[:2000]}])
        if pi_result and len(pi_result) > 0:
            classification = pi_result[0].get("classification", "UNSURE")
            confidence = pi_result[0].get("confidence", 0.0)
            logger.info(f"Pi classifier: {name} → {classification} ({confidence:.0%})")

            if classification == "NOISE" and confidence >= 0.8:
                summary = f"No urgent {name} updates."
                with open(cache_file, "w") as f:
                    f.write(summary)
                logger.info(f"Pi classifier marked {name} as NOISE — skipping agy entirely")
                return summary

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
            except Exception as e:
                logger.debug("rules_file unreadable, proceeding without: %r", e)

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
        from utils import mark_processed as _mark_processed
        _mark_processed(name, data[:1000])
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
    # Rotate combined_summaries.txt to prevent unbounded growth
    from utils import rotate_file_if_needed
    from config import MAX_COMBINED_SUMMARIES_CHARS
    rotate_file_if_needed(Path(combined_summaries_path), MAX_COMBINED_SUMMARIES_CHARS)
        
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
        except Exception as e:
            logger.debug("Malformed tasks JSON from LLM (left empty): %r", e)
        digest = digest.replace('TASKS_JSON:' + tasks_match.group(1), '').strip()

    topics_match = _re.search(r'STUDY_TOPICS_JSON:(.*?)(?:TASKS_JSON:|$)', digest, _re.DOTALL)
    if topics_match:
        try:
            topics = json.loads(topics_match.group(1).strip())
        except Exception as e:
            logger.debug("Malformed topics JSON from LLM (left empty): %r", e)
        digest = digest.replace('STUDY_TOPICS_JSON:' + topics_match.group(1).split('\n')[0], '').strip()

    # ── Deduplication: bullet-level comparison using persistent hash set ────
    # Uses seen_bullets.json to track ALL bullets ever seen, preventing
    # oscillation where old bullets are forgotten and re-notified.
    import re as _re
    previous_digest_path = LATEST_DIGEST_FILE
    seen_bullets_path = CACHE_DIR / "seen_bullets.json"
    seen_bullets: set = set()
    try:
        if seen_bullets_path.exists():
            seen_bullets = set(json.loads(seen_bullets_path.read_text()))
    except Exception as e:
        logger.debug("seen_bullets unreadable, starting fresh: %r", e)

    if seen_bullets:
        kept = []
        new_bullet_count = 0
        for line in digest.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("•", "-", "✅", "📎", "▶️")):
                normalized = _re.sub(r'[^\w\s]', '', stripped).strip().lower()
                if normalized not in seen_bullets:
                    kept.append(line)
                    seen_bullets.add(normalized)
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
    else:
        # First run: seed the persistent set with all current bullets
        for line in digest.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("•", "-", "✅", "📎", "▶️")):
                normalized = _re.sub(r'[^\w\s]', '', stripped).strip().lower()
                seen_bullets.add(normalized)

    # Persist seen bullets (cap at 5000 to prevent unbounded growth)
    try:
        bullet_list = list(seen_bullets)
        if len(bullet_list) > 5000:
            bullet_list = bullet_list[-5000:]
        seen_bullets_path.write_text(json.dumps(bullet_list))
        logger.info(f"Persisted {len(bullet_list)} seen bullets to {seen_bullets_path}")
    except Exception as e:
        logger.error(f"Failed to persist seen bullets: {e}")

    # Save deduped digest to latest_digest.txt for display
    try:
        with open(previous_digest_path, "w") as f:
            f.write(digest)
    except Exception as e:
        logger.error(f"Failed to save digest: {e}")

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

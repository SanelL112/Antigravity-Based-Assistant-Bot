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
        "You are summarizing Canvas data for Sanel Lathiya's personal assistant bot.\n"
        "Given the raw Canvas data below, produce a SHORT plain-text summary (max 5 bullet points).\n"
        "Focus on: upcoming assignments, announcements, recent page updates.\n"
        "If nothing important, write: 'No urgent Canvas updates.'\n"
        "Do NOT write JSON. Just clean readable text.\n\n"
        "Raw Canvas data:\n{data}"
    ),
    "classroom": (
        "You are summarizing Google Classroom data for Sanel Lathiya's personal assistant bot.\n"
        "Given the raw Classroom assignments below, produce a SHORT plain-text summary (max 6 bullet points).\n"
        "Focus only on the MOST RECENT assignments (ignore anything older than 2 weeks if dates are given).\n"
        "If nothing important, write: 'No urgent Classroom updates.'\n"
        "Do NOT write JSON. Just clean readable text.\n\n"
        "Raw Classroom data:\n{data}"
    ),
    "gmail": (
        "You are summarizing Gmail data for Sanel Lathiya's personal assistant bot.\n"
        "Given the raw email list below, produce a SHORT plain-text summary (max 4 bullet points).\n"
        "Focus on: emails that need action or are from important senders. Skip spam/newsletters.\n"
        "If nothing important, write: 'No urgent emails.'\n"
        "Do NOT write JSON. Just clean readable text.\n\n"
        "Raw Gmail data:\n{data}"
    ),
    "groupme": (
        "You are summarizing GroupMe messages for Sanel Lathiya's personal assistant bot.\n"
        "Given the raw messages below, produce a SHORT plain-text summary (max 4 bullet points).\n"
        "Focus on: announcements, events, things Sanel might need to act on.\n"
        "If nothing important, write: 'No urgent GroupMe messages.'\n"
        "Do NOT write JSON. Just clean readable text.\n\n"
        "Raw GroupMe data:\n{data}"
    ),
    "classroom_announcements": (
        "You are summarizing Google Classroom announcements for Sanel Lathiya's personal assistant bot.\n"
        "Given the raw announcements below, produce a SHORT plain-text summary (max 6 bullet points).\n"
        "Focus only on NEW, important announcements (things teachers just posted).\n"
        "If nothing important, write: 'No new Classroom announcements.'\n"
        "Do NOT write JSON. Just clean readable text.\n\n"
        "Raw Classroom Announcements:\n{data}"
    ),
    "gdocs": (
        "You are an offline filtering AI. Read the text of these recent Google Docs.\n"
        "Extract ONLY the sentences that look like homework, assignments, or important dates.\n"
        "If there is nothing important, reply exactly with: 'No urgent docs.'\n"
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
    "Also return a JSON list of tasks on the LAST LINE in this exact format (one line):\n"
    "TASKS_JSON:[{\"id\":\"...\",\"title\":\"...\",\"source\":\"...\",\"due_date\":null,\"priority\":\"medium\",\"status\":\"Not started\",\"start_value\":0,\"end_value\":100}]\n"
    "CRITICAL: If you cannot confidently determine the 'priority', 'status', 'start_value', or 'end_value' from the text, set that specific field to 'unknown'."
)

# ── agy helper ────────────────────────────────────────────────────────────────

def call_agy(prompt: str, timeout: int = 180, model: str = "pro") -> str:
    """Call agy --print using a PTY so it doesn't hang on pipe detection."""
    import pty, select, time, os as _os
    try:
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            [AGENTAPI_BIN, "--model", model, "--print", prompt],
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
                # Drain any remaining output
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

        proc.wait(timeout=5) if proc.poll() is None else None
        try:
            _os.close(master)
        except OSError:
            pass

        raw = b"".join(output_chunks).decode("utf-8", errors="replace")
        # Strip ANSI escape codes and carriage returns
        import re
        clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', raw)
        clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()
        return clean

    except subprocess.TimeoutExpired:
        logger.error(f"agy timed out after {timeout}s")
        try:
            proc.kill()
        except Exception:
            pass
        return ""
    except Exception as e:
        logger.error(f"agy pty error: {e}")
        return ""

def call_local_llm(prompt: str) -> str:
    """Calls Qwen2 0.5B via Ollama for fast, local, offline filtering."""
    import requests
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2:0.5b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=120.0
        )
        if res.status_code == 200:
            return res.json().get("response", "").strip()
        else:
            logger.error(f"Ollama returned {res.status_code}")
            return "Could not summarize locally."
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
        return "Local LLM offline."



# ── Per-source processing ─────────────────────────────────────────────────────

def process_source(name: str, data: str) -> str:
    """Run agy for a single source. Saves result to cache file. Returns summary text."""
    cache_file = os.path.join(CACHE_DIR, f"{name}_summary.txt")

    if not data or data.strip() == "" or "not configured" in data.lower():
        summary = f"No {name} data available."
        with open(cache_file, "w") as f:
            f.write(summary)
        return summary

    # Trim to 1500 chars per source to keep the local LLM call fast and prevent context overflow
    trimmed = data[:1500] + ("\n[...trimmed...]" if len(data) > 1500 else "")
    prompt = SOURCE_PROMPTS[name].format(data=trimmed)
    logger.info(f"Calling LOCAL Qwen2 0.5B for {name} ({len(prompt)} chars)...")

    summary = call_local_llm(prompt)
    if not summary:
        summary = f"Could not summarize {name} data locally."

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

    # Save combined summaries to file for reference
    with open(os.path.join(CACHE_DIR, "combined_summaries.txt"), "w") as f:
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
    output = call_agy(prompt, timeout=180)

    if not output:
        return {"tasks": [], "digest": ""}

    # Split tasks JSON from the digest text
    tasks = []
    digest = output
    if "TASKS_JSON:" in output:
        parts = output.rsplit("TASKS_JSON:", 1)
        digest = parts[0].strip()
        try:
            tasks = json.loads(parts[1].strip())
        except Exception:
            tasks = []

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

    return {"tasks": tasks, "digest": digest}


# ── Main entry point ──────────────────────────────────────────────────────────

def process_all_sources(canvas_data: str, classroom_data: str, gmail_data: str, groupme_data: str, classroom_ann_data: str = "No recent announcements.", gdocs_data: str = "No recent docs.") -> dict:
    """Passes all raw data through the AI pipeline."""
    
    # 1. Summarize each source (could run in parallel, but sequential is fine for now)
    logger.info("Summarizing Canvas...")
    canvas_summary = process_source("canvas", canvas_data)
    
    logger.info("Summarizing Google Classroom Assignments...")
    classroom_summary = process_source("classroom", classroom_data)
    
    logger.info("Summarizing Google Classroom Announcements...")
    classroom_ann_summary = process_source("classroom_announcements", classroom_ann_data)
    
    logger.info("Summarizing Gmail...")
    gmail_summary = process_source("gmail", gmail_data)
    
    logger.info("Summarizing GroupMe...")
    groupme_summary = process_source("groupme", groupme_data)
    
    logger.info("Summarizing Google Docs...")
    gdocs_summary = process_source("gdocs", gdocs_data)
    
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

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
}

DIGEST_ASSEMBLY_PROMPT = (
    "You are Sanel Lathiya's personal assistant bot. "
    "Below are pre-processed summaries from each data source. "
    "Assemble them into ONE beautifully formatted Markdown digest message to send via Telegram.\n\n"
    "Rules:\n"
    "- Use emoji section headers: 📚 Canvas, 🏫 Google Classroom, 📧 Gmail, 💬 GroupMe\n"
    "- Keep each section concise. Skip sections that say 'No urgent updates'.\n"
    "- End with a friendly one-liner.\n"
    "- Return ONLY the Markdown text, no JSON, no explanation.\n\n"
    "Summaries:\n{summaries}\n\n"
    "Also return a JSON list of tasks on the LAST LINE in this exact format (one line):\n"
    "TASKS_JSON:[{{\"id\":\"...\",\"title\":\"...\",\"source\":\"...\",\"due_date\":null,\"url\":null}}]"
)

# ── agy helper ────────────────────────────────────────────────────────────────

def call_agy(prompt: str, timeout: int = 180) -> str:
    """Call agy --print using a PTY so it doesn't hang on pipe detection."""
    import pty, select, time, os as _os
    try:
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            [AGENTAPI_BIN, "--print", prompt],
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


# ── Per-source processing ─────────────────────────────────────────────────────

def process_source(name: str, data: str) -> str:
    """Run agy for a single source. Saves result to cache file. Returns summary text."""
    cache_file = os.path.join(CACHE_DIR, f"{name}_summary.txt")

    if not data or data.strip() == "" or "not configured" in data.lower():
        summary = f"No {name} data available."
        with open(cache_file, "w") as f:
            f.write(summary)
        return summary

    # Trim to 1500 chars per source to keep each agy call fast
    trimmed = data[:1500] + ("\n[...trimmed...]" if len(data) > 1500 else "")
    prompt = SOURCE_PROMPTS[name].format(data=trimmed)
    logger.info(f"Calling agy for {name} ({len(prompt)} chars)...")

    summary = call_agy(prompt, timeout=180)
    if not summary:
        summary = f"Could not summarize {name} data."

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
            tasks_raw = parts[1].strip()
            tasks = json.loads(tasks_raw)
        except Exception:
            tasks = []

    # Save final digest to file
    with open(os.path.join(BOT_DIR, "latest_digest.txt"), "w") as f:
        f.write(digest)

    return {"tasks": tasks, "digest": digest}


# ── Main entry point ──────────────────────────────────────────────────────────

def process_all_sources(canvas_data="", classroom_data="", gmail_data="", groupme_data="") -> dict:
    """Process each source separately via agy, then assemble into final digest."""
    sources = {
        "canvas": canvas_data,
        "classroom": classroom_data,
        "gmail": gmail_data,
        "groupme": groupme_data,
    }

    summaries = {}
    for name, data in sources.items():
        summaries[name] = process_source(name, data)

    return assemble_digest(summaries)

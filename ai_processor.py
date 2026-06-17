"""
ai_processor.py - Uses agy --print to filter scraped data into tasks and alerts.
"""

import json
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")

SYSTEM_PROMPT = """You are a personal assistant AI summarizing data for Sanel Lathiya.

Return ONLY a raw JSON object (no markdown, no explanation) with two keys:

1. "tasks": A list of action items the user needs to complete.
   - Include: Canvas/Classroom assignments due soon or recently posted.
   - Exclude: Old completed work.
   - Each task: {"id": str (exact assignment name), "title": str, "source": str, "due_date": str or null, "url": str or null}

2. "digest": A single, beautifully formatted Markdown string that summarizes EVERYTHING from the scraped data.
   - This will be sent to the user as a digest message.
   - Summarize the new assignments, important emails, and GroupMe conversations in a friendly, readable format.
   - Group by source (e.g., 📚 Canvas, 📧 Gmail, 💬 GroupMe).
   - Filter out complete junk (like spam), but summarize the rest nicely.
   - If there is absolutely no data, make the digest string empty ("").

Return ONLY valid JSON like: {"tasks": [...], "digest": "..."}"""


def trim_data(raw: str, max_chars: int = 3000) -> str:
    """Trim raw data to avoid overwhelming agy with too much text."""
    if len(raw) <= max_chars:
        return raw
    # Keep first max_chars characters and note truncation
    return raw[:max_chars] + "\n\n[...data trimmed to fit context limit...]"


def trim_classroom(data: str, max_items: int = 8) -> str:
    """Keep only the most recent N classroom assignments."""
    if not data:
        return data
    lines = data.strip().split("\n")
    # First line is the header
    header = lines[0] if lines else ""
    items = [l for l in lines[1:] if l.strip()]
    # Take only the most recent assignments (first N, since they're listed newest first)
    trimmed = items[:max_items]
    if len(items) > max_items:
        trimmed.append(f"...and {len(items) - max_items} older assignments not shown.")
    return header + "\n" + "\n".join(trimmed)


def trim_groupme(data: str, max_chars: int = 800) -> str:
    """Trim GroupMe messages to avoid huge blobs of text."""
    if not data or len(data) <= max_chars:
        return data
    return data[:max_chars] + "\n[...messages trimmed...]"


def trim_gmail(data: str, max_chars: int = 600) -> str:
    """Trim Gmail data."""
    if not data or len(data) <= max_chars:
        return data
    return data[:max_chars] + "\n[...emails trimmed...]"


def ask_agy(raw_data: str) -> dict:
    prompt = SYSTEM_PROMPT + "\n\nHere is the raw data:\n\n" + raw_data
    logger.info(f"Calling agy --print for data filtering (prompt size: {len(prompt)} chars)...")
    try:
        env = os.environ.copy()
        # Isolate the scraper's conversation history from the user's chat history
        env["HOME"] = "/home/sanel/scraper_home"
        os.makedirs("/home/sanel/scraper_home", exist_ok=True)
        result = subprocess.run(
            [AGENTAPI_BIN, "--print", prompt],
            capture_output=True, text=True, timeout=300, env=env
        )
        output = result.stdout.strip()
        if not output:
            logger.error(f"agy returned no output. stderr: {result.stderr[:300]}")
            return {"tasks": [], "digest": ""}

        # Strip markdown fences if present
        clean = output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(clean[start:end])
                except Exception:
                    pass
            logger.error(f"Could not parse JSON from agy response: {clean[:300]}")
            return {"tasks": [], "digest": ""}
    except subprocess.TimeoutExpired:
        logger.error("agy --print timed out after 300 seconds")
        return {"tasks": [], "digest": ""}
    except Exception as e:
        logger.error(f"agy --print failed: {e}")
        return {"tasks": [], "digest": ""}


def process_all_sources(canvas_data="", classroom_data="", gmail_data="", groupme_data="") -> dict:
    parts = []
    if canvas_data:
        parts.append(f"=== CANVAS ===\n{trim_data(canvas_data, 500)}")
    if classroom_data:
        trimmed_classroom = trim_classroom(classroom_data, max_items=8)
        parts.append(f"=== GOOGLE CLASSROOM (most recent 8 assignments) ===\n{trimmed_classroom}")
    if gmail_data:
        parts.append(f"=== GMAIL ===\n{trim_gmail(gmail_data)}")
    if groupme_data:
        parts.append(f"=== GROUPME ===\n{trim_groupme(groupme_data)}")
    if not parts:
        return {"tasks": [], "digest": ""}
    combined = "\n\n".join(parts)
    logger.info(f"Total data size sent to agy: {len(combined)} chars")
    return ask_agy(combined)

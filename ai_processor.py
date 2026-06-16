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


def ask_agy(raw_data: str) -> dict:
    prompt = SYSTEM_PROMPT + "\n\nHere is the raw data:\n\n" + raw_data
    logger.info("Calling agy --print for data filtering...")
    try:
        env = os.environ.copy()
        # Isolate the scraper's conversation history from the user's chat history
        env["HOME"] = "/home/sanel/scraper_home"
        os.makedirs("/home/sanel/scraper_home", exist_ok=True)
        result = subprocess.run(
            [AGENTAPI_BIN, "--print", prompt],
            capture_output=True, text=True, timeout=120, env=env
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
    except Exception as e:
        logger.error(f"agy --print failed: {e}")
        return {"tasks": [], "digest": ""}


def process_all_sources(canvas_data="", classroom_data="", gmail_data="", groupme_data="") -> dict:
    parts = []
    if canvas_data:
        parts.append(f"=== CANVAS ===\n{canvas_data}")
    if classroom_data:
        parts.append(f"=== GOOGLE CLASSROOM ===\n{classroom_data}")
    if gmail_data:
        parts.append(f"=== GMAIL ===\n{gmail_data}")
    if groupme_data:
        parts.append(f"=== GROUPME ===\n{groupme_data}")
    if not parts:
        return {"tasks": [], "digest": ""}
    return ask_agy("\n\n".join(parts))

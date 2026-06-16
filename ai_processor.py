"""
ai_processor.py - Uses agy --print to filter scraped data into tasks and alerts.
"""

import json
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")

SYSTEM_PROMPT = """You are a personal assistant AI filtering raw scraped data for Sanel Lathiya.

Return ONLY a raw JSON object (no markdown, no explanation) with two lists:

1. "tasks": Action items the user needs to complete.
   - Include: Canvas/Classroom assignments due soon or recently posted.
   - Exclude: Old completed work, spam, promotional content.
   - Each task: {"title": str, "source": str, "due_date": str or null, "url": str or null}

2. "alerts": Important notifications to know about NOW.
   - Include: GroupMe announcements, urgent emails from real people or school.
   - Exclude: College recruitment emails, LinkedIn spam, marketing, casual chatter.
   - Each alert: {"summary": str, "source": str, "from": str}

Return ONLY valid JSON like: {"tasks": [...], "alerts": [...]}"""


def ask_agy(raw_data: str) -> dict:
    prompt = SYSTEM_PROMPT + "\n\nHere is the raw data:\n\n" + raw_data
    logger.info("Calling agy --print for data filtering...")
    try:
        result = subprocess.run(
            [AGENTAPI_BIN, "--print", "--model=flash", prompt],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout.strip()
        if not output:
            logger.error(f"agy returned no output. stderr: {result.stderr[:300]}")
            return {"tasks": [], "alerts": []}

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
            return {"tasks": [], "alerts": []}
    except Exception as e:
        logger.error(f"agy --print failed: {e}")
        return {"tasks": [], "alerts": []}


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
        return {"tasks": [], "alerts": []}
    return ask_agy("\n\n".join(parts))

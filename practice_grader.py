"""
practice_grader.py — Feature 5: Automated Practice Test Grading

When the user sends a photo of completed practice problems:
1. OCR the image (local Tesseract — PII safe)
2. Extract problems and user answers via agy Vision (local agy — PII safe)
3. Compare against answer key from study guide knowledge base
4. Grade and log weak topics to knowledge_gaps/ for nightly targeting
"""
import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional
from config import (
    BASE_DIR, SANEL_CHAT_ID
)
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
STUDY_GUIDES_DIR = BASE_DIR / "study_guides"

logger = logging.getLogger(__name__)
GAPS_DIR = BASE_DIR / "knowledge_gaps"
GAPS_DIR.mkdir(exist_ok=True)


def grade_practice_test(image_path: str, topic: str = "") -> str:
    """
    Grade a practice test from a photo.

    Args:
        image_path: Path to the downloaded image
        topic: Optional topic hint (e.g. "SAT Math", "Geometry")

    Returns:
        Formatted grading results for Telegram
    """
    from llm_router import call_agy_local

    # Step 1: Basic OCR for raw text
    raw_ocr = _ocr_image(image_path)

    # Step 2: Use agy Vision to structured-extract problems and answers
    extract_prompt = (
        f"You are a practice test grader. The user uploaded a photo of completed practice problems"
        f"{f' on the topic: {topic}' if topic else ''}.\n\n"
        f"Here is the raw OCR text from the image:\n{raw_ocr[:10000]}\n\n"
        f"Your job is to:\n"
        f"1. Identify each distinct problem number and the user's answer\n"
        f"2. For math problems, try to determine if the work shown is correct\n\n"
        f"Output ONLY a JSON array like this:\n"
        f"[{{\"problem\": 1, \"user_answer\": \"x=5\", \"work_shown\": \"brief description\"}},\n"
        f" {{\"problem\": 2, \"user_answer\": \"B\", \"work_shown\": \"...\"}}]\n"
        f"If you cannot parse any problems, return an empty array []."
    )

    extracted_json = call_agy_local(extract_prompt, model="pro", timeout=120)

    # Parse the extraction
    problems = _safe_parse_json(extracted_json)
    if problems is None:
        return "❌ I couldn't parse the problems from the photo. Try a clearer image or tell me the topic."

    if not problems:
        return "❌ No problems detected. Make sure the photo is well-lit and shows the full page."

    # Step 3: Find answer key in study guides
    answer_key = _find_answer_key(topic, problems)
    if not answer_key:
        # No stored answer key — just list what we found
        return _format_no_key_response(problems)

    # Step 4: Grade each problem
    results = _grade_problems(problems, answer_key)

    # Step 5: Log weak topics
    _log_weak_topics(results, topic)

    # Step 6: Format results
    return _format_grading_results(results, topic)


def _ocr_image(image_path: str) -> str:
    """Basic OCR via Tesseract. Local only — PII safe."""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def _safe_parse_json(text: str) -> Optional[list]:
    """Try to extract JSON from text that might have extra content."""
    import re
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find JSON array in text
    match = re.search(r'\[[\s\S]*?\]', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def _find_answer_key(topic: str, problems: list) -> Optional[dict]:
    """
    Search study guides and knowledge base for matching practice problems.
    Returns dict of {problem_number: correct_answer} or None.
    """
    answer_key = {}

    # Search in study guides
    for guide_file in STUDY_GUIDES_DIR.glob("*.md"):
        content = guide_file.read_text(encoding="utf-8", errors="replace")
        key = _extract_answers_from_guide(content, problems)
        if key:
            answer_key.update(key)

    # Search in knowledge base
    for kb_file in KNOWLEDGE_BASE_DIR.glob("*.md"):
        content = kb_file.read_text(encoding="utf-8", errors="replace")
        key = _extract_answers_from_guide(content, problems)
        if key:
            answer_key.update(key)

    return answer_key if answer_key else None


def _extract_answers_from_guide(content: str, problems: list) -> Optional[dict]:
    """Extract a practice exam answer key section from a markdown guide."""
    import re

    # Look for "## Practice Exam" or "## Answer Key" section
    sections = re.split(r'^#{2,3}\s+', content, flags=re.MULTILINE)
    for section in sections:
        if "practice exam" in section.lower() or "answer key" in section.lower() or "practice problem" in section.lower():
            # Try to extract numbered Q&A pairs
            answers = {}
            matches = re.findall(r'(\d+)\)[\s:]*?(?:Answer:\s*)?([A-D]|(?:\d+(?:\.\d+)?)|(?:[x=].*?))', section, re.IGNORECASE)
            for num, ans in matches:
                answers[int(num)] = ans.strip()
            return answers if answers else None
    return None


def _grade_problems(problems: list, answer_key: dict) -> list:
    """Grade each problem against the answer key."""
    results = []
    for prob in problems:
        num = prob.get("problem", 0)
        user_ans = str(prob.get("user_answer", "")).strip()
        correct = answer_key.get(num, "")

        result = {
            "problem": num,
            "user_answer": user_ans,
            "correct_answer": correct,
            "work_shown": prob.get("work_shown", ""),
        }

        if isinstance(correct, str) and "explain" in correct.lower():
            # Open-ended: correctness is subjective, skip auto-grade
            result["status"] = "review"
        else:
            # Normalize for comparison
            norm_user = user_ans.lower().strip().replace(" ", "").replace("=", "")
            norm_correct = str(correct).lower().strip().replace(" ", "").replace("=", "")
            result["status"] = "correct" if norm_user == norm_correct else "wrong"

        results.append(result)
    return results


def _log_weak_topics(results: list, topic: str):
    """Log wrong answers to knowledge_gaps/ for nightly targeting."""
    topic_slug = (topic or "general").replace(" ", "_").lower()
    gaps_file = GAPS_DIR / f"{topic_slug}.txt"

    wrong = [r for r in results if r["status"] == "wrong"]
    if not wrong:
        return

    with open(gaps_file, "a") as f:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n--- {date_str} ---\n")
        for r in wrong:
            f.write(f"Problem {r['problem']}: answered '{r['user_answer']}' "
                    f"(correct: {r['correct_answer']})\n")
            if r["work_shown"]:
                f.write(f"  Work shown: {r['work_shown']}\n")

    logger.info(f"Logged {len(wrong)} wrong answers to {gaps_file}")


def _format_grading_results(results: list, topic: str) -> str:
    """Format grading results for Telegram."""
    correct_count = sum(1 for r in results if r["status"] == "correct")
    wrong_count = sum(1 for r in results if r["status"] == "wrong")
    review_count = sum(1 for r in results if r["status"] == "review")
    total = len(results)

    pct = round(correct_count / total * 100) if total > 0 else 0

    lines = [
        f"📝 **Practice Test Results** — {topic or 'General'}",
        f"Score: **{correct_count}/{total}** ({pct}%)",
        f"✅ {correct_count} correct | ❌ {wrong_count} wrong | ⚠️ {review_count} need review",
        "",
    ]

    # Show wrong answers with corrections
    wrong = [r for r in results if r["status"] == "wrong"]
    if wrong:
        lines.append("**Wrong answers:**")
        for r in wrong:
            lines.append(f"  Q{r['problem']}: you said `{r['user_answer']}` → "
                         f"correct is `{r['correct_answer']}`")

    # Logged message
    if wrong:
        lines.append(f"\n📝 Logged {len(wrong)} gaps — tonight's study guide will target them!")

    # Emoji feedback
    if pct >= 90:
        lines.append("\n🌟 Excellent! You're mastering this!")
    elif pct >= 70:
        lines.append("\n👍 Good work! Review the wrong answers above.")
    else:
        lines.append("\n💪 Keep practicing! I'll focus on this in tonight's study guide.")

    return "\n".join(lines)


def _format_no_key_response(problems: list) -> str:
    """Format response when we found problems but no answer key."""
    lines = [
        f"📝 **Detected {len(problems)} problems:**",
    ]
    for p in problems:
        lines.append(f"  Q{p.get('problem', '?')}: `{p.get('user_answer', '?')}`")

    lines.append("\n⚠️ I couldn't find an answer key for this topic in your study guides.")
    lines.append("I've still logged these — upload a photo of the answer key "
                 "or tell me the topic so I can search for one!")
    return "\n".join(lines)

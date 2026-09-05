"""OneNote harvest-cache alerts and the "From your notebooks" digest section.

Phase 1 of the OneNote roadmap (see ``docs/ONENOTE_CONTEXT.md`` §6):

1. **RAG retention** — ``save_harvested_page`` in ``onenote_web_scraper`` writes
   each harvested page's reading-order text to ``source_cache/onenote_pages/``,
   which the embedding indexer scans (``embedding_indexer.collect_sources``).
2. **New-task alerts** — the daemon's harvest cache
   (``cache/onenote_page_extractions.json``) is diffed between runs; newly seen
   *upcoming-dated* items are pushed through the existing Telegram plumbing by
   ``main._check_updates_impl``.  Seen task ids persist in
   ``cache/onenote_seen_tasks.json`` so an item alerts exactly once.
3. **Digest section** — ``notebooks_section`` renders a deterministic third
   digest section (new pages this week + upcoming OneNote items), appended by
   ``ai_processor.assemble_digest`` and deduped like every other bullet.

Pure-file module: no network, no browser.  Every entry point defaults to
``config.CACHE_DIR`` and accepts an explicit directory for hermetic tests.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Upcoming = today .. today + HORIZON_DAYS (mirrors topic_discovery's +60d window).
HORIZON_DAYS = 60
# A page counts as "new this week" for NEW_PAGE_DAYS days after first being seen.
NEW_PAGE_DAYS = 7
# Section caps keep the digest message far under Telegram's 4096-char limit.
MAX_UPCOMING = 5
MAX_NEW_PAGES = 4
# Seen-id history cap: >500 entries is just re-seen noise.
MAX_SEEN_IDS = 500

_CACHE_FILENAME = "onenote_page_extractions.json"
_SEEN_TASKS_FILENAME = "onenote_seen_tasks.json"
_PAGES_FIRST_SEEN_FILENAME = "onenote_pages_first_seen.json"

# Page titles that read as schedule scaffolding, never as notebook content.
_PAGE_TITLE_JUNK_RE = re.compile(
    r"\b(calendar|agenda|advisement|syllabus|handbook|observe|signature)\b",
    re.IGNORECASE,
)
# Task-title keywords that make a row school scaffolding rather than a task;
# mirrors the filter topic_discovery applies so alerts never push advisement/
# syllabus/observer pages as study work.
_TASK_TITLE_JUNK_RE = re.compile(
    r"\b(advisement|syllabus|handbook|observe|signature)\b", re.IGNORECASE
)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _cache_dir(cache_dir: Path | None = None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    from config import CACHE_DIR

    return CACHE_DIR


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── Task flattening + upcoming window ────────────────────────────────────────

def _flatten_cache(cache: Any) -> list[tuple[str, dict]]:
    """Return ``(page_key, task)`` pairs from the harvest cache.

    The daemon writes ``{page_key: [task dicts]}``; page keys look like
    ``"Notebook/Section/Page title"``.
    """
    pairs: list[tuple[str, dict]] = []
    if not isinstance(cache, dict):
        return pairs
    for page_key, tasks in cache.items():
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if isinstance(task, dict):
                pairs.append((str(page_key), task))
    return pairs


def _task_stable_id(page_key: str, task: dict) -> str:
    title = str(task.get("title") or "").strip()
    due = str(task.get("due_date") or "")[:10]
    raw = f"{page_key}|{title}|{due}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:24]


def _upcoming_rows(cache: Any, today: date | None = None) -> list[dict]:
    """Actionable OneNote tasks due within [today, today + HORIZON_DAYS].

    Filters with the shared junk-title gate (``assignment_calendar._is_junk_title``)
    and the extractor's title cleaner, so schedule scaffolding never alerts.
    Rows are sorted by due date and deduped on ``(title, due)``.
    """
    from scrapers.assignment_calendar import _is_junk_title
    from scrapers.canvas_page_extractor import _clean_task_title

    today = today or date.today()
    horizon = today + timedelta(days=HORIZON_DAYS)
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for page_key, task in _flatten_cache(cache):
        title = _clean_task_title(str(task.get("title") or ""))
        due = str(task.get("due_date") or "")[:10]
        if not title or not _ISO_DATE_RE.fullmatch(due) or _is_junk_title(title):
            continue
        if _TASK_TITLE_JUNK_RE.search(title):
            continue
        try:
            due_date = date.fromisoformat(due)
        except ValueError:
            continue
        if not (today <= due_date <= horizon):
            continue
        dedupe = (title.lower(), due)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        notebook = str(task.get("course") or "").strip() or page_key.split("/")[0]
        rows.append(
            {
                "title": title,
                "due_date": due,
                "notebook": notebook,
                "page_key": page_key,
                "id": _task_stable_id(page_key, task),
            }
        )
    rows.sort(key=lambda r: (r["due_date"], r["title"].lower()))
    return rows


# ── Item 2: new-task Telegram alerts ────────────────────────────────────────

def check_new_onenote_alerts(
    cache_dir: Path | None = None, today: date | None = None
) -> str:
    """Return a compact alert message for newly seen upcoming OneNote tasks.

    Diffs the harvest cache against the persisted seen-id set
    (``cache/onenote_seen_tasks.json``).  New upcoming items are rendered and
    their ids persisted, so each item alerts exactly once.  Returns ``""`` when
    there is nothing new (or no cache).  Never raises.
    """
    from bot.storage import AtomicJSONStore

    base = _cache_dir(cache_dir)
    cache = _load_json(base / _CACHE_FILENAME)
    if not isinstance(cache, dict) or not cache:
        return ""

    store = AtomicJSONStore(base / _SEEN_TASKS_FILENAME, list)
    try:
        seen = {str(x) for x in store.read() if isinstance(x, str)}
    except Exception:
        seen = set()

    rows = _upcoming_rows(cache, today)
    fresh = [r for r in rows if r["id"] not in seen]
    if not fresh:
        return ""

    try:
        store.write(list(seen)[-MAX_SEEN_IDS:] + [r["id"] for r in fresh])
    except Exception as exc:  # alert must still fire even if persistence fails
        logger.warning("Could not persist OneNote seen ids: %s", exc)

    return _render_alert(fresh)


def _render_alert(rows: list[dict], limit: int = 6) -> str:
    """Markdown message: new OneNote tasks with their due dates."""
    if not rows:
        return ""
    from utils import sanitize_markdown

    lines = [
        f"• {sanitize_markdown(r['title'])} — due {r['due_date']} "
        f"({sanitize_markdown(r['notebook'])})"
        for r in rows[:limit]
    ]
    message = "📓 **New from your notebooks**\n" + "\n".join(lines)
    extra = len(rows) - limit
    if extra > 0:
        message += f"\n…and {extra} more"
    return message


# ── Item 3: "From your notebooks" digest section ────────────────────────────

def _page_title(page_key: str) -> str:
    return page_key.rsplit("/", 1)[-1].strip()


def _is_junk_page(page_key: str) -> bool:
    title = _page_title(page_key)
    if not title:
        return True
    if _PAGE_TITLE_JUNK_RE.search(title):
        return True
    from scrapers.topic_discovery import _is_date_only_title

    return _is_date_only_title(title)


def notebooks_section(cache_dir: Path | None = None, today: date | None = None) -> str:
    """Render the deterministic "From your notebooks" digest section.

    Includes:
      * pages first seen within the last ``NEW_PAGE_DAYS`` days
        (first-seen tracked in ``cache/onenote_pages_first_seen.json``), and
      * OneNote tasks due within the upcoming ``HORIZON_DAYS`` window.

    Returns ``""`` when there is nothing to show.  Never raises — a missing or
    corrupt cache simply produces an empty section.
    """
    base = _cache_dir(cache_dir)
    today = today or date.today()
    cache = _load_json(base / _CACHE_FILENAME)
    if not isinstance(cache, dict) or not cache:
        return ""

    # New pages this week — first-seen tracking, persisted.
    from bot.storage import AtomicJSONStore

    first_seen: dict[str, str] = {}
    seen_store = AtomicJSONStore(base / _PAGES_FIRST_SEEN_FILENAME, dict)
    try:
        raw = seen_store.read()
        if isinstance(raw, dict):
            first_seen = {str(k): str(v) for k, v in raw.items()}
    except Exception:
        first_seen = {}

    new_pages: list[str] = []
    for page_key in cache:
        if _is_junk_page(page_key):
            continue
        first_date = first_seen.get(page_key)
        if not first_date:
            first_date = today.isoformat()
            first_seen[page_key] = first_date
        if today - date.fromisoformat(first_date) < timedelta(days=NEW_PAGE_DAYS):
            new_pages.append(page_key)
    new_pages.sort()

    if new_pages:
        try:
            seen_store.write(dict(list(first_seen.items())[-500:]))
        except Exception as exc:
            logger.warning("Could not persist OneNote first-seen pages: %s", exc)

    upcoming = _upcoming_rows(cache, today)

    parts: list[str] = []
    if new_pages:
        lines = [
            f"• New this week: {_page_title(p)} ({_notebook_of(p)})"
            for p in new_pages[:MAX_NEW_PAGES]
        ]
        parts.append("\n".join(lines))
    if upcoming:
        lines = [
            f"• Upcoming: {r['title']} — due {r['due_date']} ({r['notebook']})"
            for r in upcoming[:MAX_UPCOMING]
        ]
        parts.append("\n".join(lines))
    if not parts:
        return ""
    return "📓 **From your notebooks**\n" + "\n\n".join(parts)


def _notebook_of(page_key: str) -> str:
    return page_key.split("/")[0].strip()
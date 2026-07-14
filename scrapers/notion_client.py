import os
import requests
import logging
import time as _time
import threading
import config

logger = logging.getLogger(__name__)

NOTION_API_KEY = config.NOTION_API_KEY
DATABASE_ID = config.NOTION_DATABASE_ID  # Tracker database

# ── Rate Limiter (Notion: 3 req/s) ──────────────────────────────────────────
class _RateLimiter:
    def __init__(self, min_interval=0.35):
        self.min_interval = min_interval
        self.last_call = 0
        self.lock = threading.Lock()

    def wait(self):
        # Calculate sleep time under lock, then sleep outside lock
        with self.lock:
            elapsed = _time.time() - self.last_call
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
            else:
                sleep_time = 0
            self.last_call = _time.time() + sleep_time
        
        # Sleep outside the lock to avoid blocking other threads
        if sleep_time > 0:
            _time.sleep(sleep_time)

_notion_limiter = _RateLimiter()


def _rate_limited_request(method, url, **kwargs):
    """Make a rate-limited HTTP request."""
    _notion_limiter.wait()
    resp = requests.request(method, url, **kwargs)
    # Retry on 429
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", 1.0))
        logger.warning(f"Notion rate limited, waiting {retry_after}s")
        _time.sleep(retry_after)
        _notion_limiter.wait()
        resp = requests.request(method, url, **kwargs)
    return resp
OWNER_ID = "2f9d872b-594c-8115-84a6-00028eb47924"     # Sanel Lathiya

# Schema reference (read-only formula fields, do NOT set these):
#   Progress     → formula (auto: start/end values)
#   Days until due → formula (auto: days from today to due date)

PRIORITY_OPTIONS = {"high", "medium", "low"}
STATUS_OPTIONS   = {"Not started", "In progress", "Done"}


def task_exists(title: str, headers: dict, fuzzy: bool = True) -> bool:
    """
    Check if a task with this title (or similar) already exists.

    Fast path: exact match via Notion filter (O(1) query).
    Slow path: fuzzy scan of all non-Done tasks (only if no exact match).
    """
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    norm_title = title.lower().strip()

    # ── Fast path: exact match ──────────────────────────────────────────
    exact_payload = {
        "page_size": 1,
        "filter": {
            "and": [
                {"property": "Task name", "title": {"equals": title}},
                {"property": "Status", "status": {"does_not_equal": "Done"}},
            ]
        }
    }
    try:
        res = _rate_limited_request("POST", query_url, headers=headers, json=exact_payload, timeout=10)
        res.raise_for_status()
        if len(res.json().get("results", [])) > 0:
            logger.info(f"Task '{title}' already exists (exact match). Skipping.")
            return True
    except Exception as e:
        logger.error(f"Notion exact-match query failed: {e}")

    # ── Slow path: fuzzy scan of all non-Done tasks ─────────────────────
    if not fuzzy:
        return False

    fuzzy_payload = {
        "page_size": 100,
        "filter": {"property": "Status", "status": {"does_not_equal": "Done"}}
    }
    try:
        res = _rate_limited_request("POST", query_url, headers=headers, json=fuzzy_payload, timeout=10)
        res.raise_for_status()
        results = res.json().get("results", [])

        import difflib
        for r in results:
            title_props = r.get("properties", {}).get("Task name", {}).get("title", [])
            existing = title_props[0].get("text", {}).get("content", "") if title_props else ""
            existing_norm = existing.lower().strip()

            similarity = difflib.SequenceMatcher(None, norm_title, existing_norm).ratio()
            if similarity > 0.75:
                logger.info(
                    f"Task '{title}' is {similarity:.0%} similar to existing "
                    f"'{existing}' — skipping as duplicate."
                )
                return True

        return False
    except Exception as e:
        logger.error(f"Notion fuzzy-dedup query failed: {e}")
        return False


def add_task_to_notion(
    title: str,
    source: str = None,
    due_date: str = None,
    url: str = None,
    priority: str = "medium",
    status: str = "Not started",
    start_value: float = None,
    end_value: float = None,
):
    """Push a new task row to the Tracker database."""
    if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key":
        logger.error("Notion API key not configured.")
        return False

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    if task_exists(title, headers):
        logger.info(f"Task '{title}' already exists in Notion. Skipping.")
        return True

    # Normalize priority
    priority = priority.lower() if priority else "medium"
    if priority not in PRIORITY_OPTIONS:
        priority = "medium"

    # Normalize status
    if status not in STATUS_OPTIONS:
        status = "Not started"

    properties = {
        # ── Required ──────────────────────────────────────────────
        "Task name": {
            "title": [{"text": {"content": title}}]
        },
        # ── Owner: always assigned to Sanel ───────────────────────
        "Owner": {
            "people": [{"object": "user", "id": OWNER_ID}]
        },
        # ── Status ────────────────────────────────────────────────
        "Status": {
            "status": {"name": status}
        },
        # ── Priority ──────────────────────────────────────────────
        "Priority": {
            "select": {"name": priority.capitalize()}
        },
    }

    # ── Due date (ISO 8601: "2026-06-25") ─────────────────────────
    if due_date and str(due_date).lower() not in ("null", "none", ""):
        try:
            properties["Due date"] = {"date": {"start": str(due_date)}}
        except Exception as e:
            logger.warning(f"Bad due_date format '{due_date}': {e}")

    # ── Start / End values (optional numbers for progress tracking) ─
    if start_value is not None:
        try:
            properties["Start value"] = {"number": float(start_value)}
        except Exception:
            pass

    if end_value is not None:
        try:
            properties["End value"] = {"number": float(end_value)}
        except Exception:
            pass

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties,
    }

    # Attach source URL as page content if provided
    children = []
    if source or url:
        lines = []
        if source:
            lines.append(f"Source: {source}")
        if url:
            lines.append(f"URL: {url}")
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "\n".join(lines)}}]
            }
        })
    if children:
        data["children"] = children

    try:
        res = _rate_limited_request(
            "POST",
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=data,
            timeout=15,
        )
        res.raise_for_status()
        page_id = res.json().get("id")
        logger.info(f"Pushed to Notion Tracker: {title} (ID: {page_id})")
        return page_id
    except Exception as e:
        logger.error(f"Failed to push to Notion: {e}")
        if "res" in locals():
            logger.error(res.text[:500])
        return None

def update_notion_task(page_id: str, priority: str = None, status: str = None, start_value: float = None, end_value: float = None):
    """Updates an existing Notion task's priority, status, or progress values."""
    if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key":
        return False
        
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    properties = {}
    if priority:
        priority = priority.lower()
        if priority in PRIORITY_OPTIONS:
            properties["Priority"] = {"select": {"name": priority.capitalize()}}
            
    if status:
        if status in STATUS_OPTIONS:
            properties["Status"] = {"status": {"name": status}}
            
    if start_value is not None:
        properties["Start value"] = {"number": float(start_value)}
        
    if end_value is not None:
        properties["End value"] = {"number": float(end_value)}
        
    if not properties:
        return True
        
    data = {"properties": properties}
    
    try:
        res = _rate_limited_request("PATCH",
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            json=data,
            timeout=15,
        )
        res.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to update Notion page {page_id}: {e}")
        return False


def archive_stale_tasks(dry_run: bool = False, max_age_days: int = 60) -> int:
    """
    Archive (mark as Done) tasks that are Not started + older than max_age_days.

    Returns the number of tasks archived.
    """
    if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key":
        logger.error("Notion API key not configured.")
        return 0

    from datetime import datetime, timezone, timedelta

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    # ── Paginate through all Not started tasks ─────────────────────────────
    payload = {
        "page_size": 100,
        "filter": {"property": "Status", "status": {"equals": "Not started"}}
    }

    archived = 0
    has_more = True
    start_cursor = None
    checked = 0

    while has_more:
        p = dict(payload)
        if start_cursor:
            p["start_cursor"] = start_cursor
        try:
            res = _rate_limited_request("POST", query_url, headers=headers, json=p, timeout=15)
            res.raise_for_status()
            data = res.json()
            results = data.get("results", [])
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        except Exception as e:
            logger.error(f"Failed to query Notion for stale tasks: {e}")
            return archived

        for task in results:
            checked += 1
            created = task.get("created_time", "")
            if not created:
                continue
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (now - created_dt).days

            if age_days < max_age_days:
                continue

            page_id = task["id"]
            title = "unknown"
            title_props = task.get("properties", {}).get("Task name", {}).get("title", [])
            if title_props:
                title = title_props[0].get("text", {}).get("content", "unknown")

            if dry_run:
                logger.info(f"[DRY RUN] Would archive: '{title}' ({age_days}d old)")
                archived += 1
            else:
                update_data = {"properties": {"Status": {"status": {"name": "Done"}}}}
                try:
                    update_res = _rate_limited_request(
                        "PATCH",
                        f"https://api.notion.com/v1/pages/{page_id}",
                        headers=headers, json=update_data, timeout=15
                    )
                    if update_res.status_code == 200:
                        logger.info(f"Archived stale task: '{title}' ({age_days}d old)")
                        archived += 1
                    else:
                        logger.warning(f"Failed to archive '{title}': HTTP {update_res.status_code}")
                except Exception as e:
                    logger.error(f"Failed to archive '{title}': {e}")

    logger.info(f"Archive complete: {archived} tasks marked Done ({'DRY RUN' if dry_run else 'LIVE'})")
    return archived


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "archive":
        dry = "--dry-run" in sys.argv
        count = archive_stale_tasks(dry_run=dry)
        print(f"{'Would archive' if dry else 'Archived'} {count} stale tasks.")
    else:
        print("Testing Notion Tracker push...")
        success = add_task_to_notion(
            title="Test Task from Bot",
            source="Canvas",
            due_date="2026-06-30",
            priority="high",
            status="Not started",
            start_value=0,
            end_value=100,
        )
        print("✅ Success! Check your Notion Tracker." if success else "❌ Failed.")

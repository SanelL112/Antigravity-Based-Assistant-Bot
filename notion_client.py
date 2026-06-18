import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = "38309c49-e758-8004-8005-c5440093e2cb"  # Tracker database
OWNER_ID = "2f9d872b-594c-8115-84a6-00028eb47924"     # Sanel Lathiya

# Schema reference (read-only formula fields, do NOT set these):
#   Progress     → formula (auto: start/end values)
#   Days until due → formula (auto: days from today to due date)

PRIORITY_OPTIONS = {"high", "medium", "low"}
STATUS_OPTIONS   = {"Not started", "In progress", "Done"}


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
        res = requests.post(
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

def update_notion_task(page_id: str, priority: str = None, status: str = None):
    """Updates an existing Notion task's priority and/or status."""
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
            
    if not properties:
        return True
        
    data = {"properties": properties}
    
    try:
        res = requests.patch(
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
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

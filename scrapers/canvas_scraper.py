import os
import logging
from canvasapi import Canvas
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN")

def get_canvas_instance():
    if not CANVAS_API_TOKEN or CANVAS_API_TOKEN == "your_canvas_api_token":
        logger.error("CANVAS_API_TOKEN is not set in .env")
        return None
    return Canvas(CANVAS_API_URL, CANVAS_API_TOKEN)

def get_upcoming_assignments():
    """Fetch recent assignments from Canvas for the current user."""
    canvas = get_canvas_instance()
    if not canvas:
        return "Canvas API token not configured."

    try:
        user = canvas.get_current_user()
        courses = list(user.get_favorite_courses())

        assignments_text = []
        for course in courses:
            try:
                # Fetch the 10 most recently updated assignments to catch new ones even without due dates
                assignments = list(course.get_assignments(order_by="updated_at", order="desc"))[:10]
                for assignment in assignments:
                    due_date = assignment.due_at if hasattr(assignment, 'due_at') and assignment.due_at else "No due date"
                    updated_at = assignment.updated_at if hasattr(assignment, 'updated_at') and assignment.updated_at else "Unknown"
                    assignments_text.append(f"[{course.name}] {assignment.name} - Due: {due_date} (Updated: {updated_at[:10]})")
            except Exception as e:
                logger.warning(f"Could not fetch assignments for {course.name}: {e}")

        if not assignments_text:
            return "No recent assignments found in your favorite courses!"

        return "📚 **Recent Canvas Assignments:**\n" + "\n".join(assignments_text)

    except Exception as e:
        logger.error(f"Error connecting to Canvas: {e}")
        return f"Error connecting to Canvas: {e}"


def get_canvas_announcements():
    """Fetch recent announcements from all active Canvas courses."""
    canvas = get_canvas_instance()
    if not canvas:
        return ""

    try:
        user = canvas.get_current_user()
        courses = list(user.get_favorite_courses())
        course_codes = [f"course_{c.id}" for c in courses]

        if not course_codes:
            return ""

        announcements = list(canvas.get_announcements(context_codes=course_codes))
        if not announcements:
            return "No recent Canvas announcements."

        lines = ["📢 **Canvas Announcements:**"]
        for a in announcements[:5]:  # limit to 5 most recent
            title = getattr(a, 'title', 'No title')
            posted = getattr(a, 'posted_at', '')
            lines.append(f"- {title}" + (f" (posted {posted[:10]})" if posted else ""))

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not fetch announcements: {e}")
        return ""


def get_canvas_pages():
    """Fetch recently updated pages from all active Canvas courses."""
    canvas = get_canvas_instance()
    if not canvas:
        return ""

    try:
        user = canvas.get_current_user()
        courses = list(user.get_favorite_courses())

        lines = ["📄 **Recently Updated Canvas Pages:**"]
        found = 0
        for course in courses:
            try:
                pages = list(course.get_pages(sort="updated_at", order="desc"))
                for page in pages[:3]:  # top 3 per course
                    title = getattr(page, 'title', 'Untitled')
                    updated = getattr(page, 'updated_at', '')
                    lines.append(f"- [{course.name}] {title}" + (f" (updated {updated[:10]})" if updated else ""))
                    found += 1
            except Exception as e:
                logger.warning(f"Could not fetch pages for {course.name}: {e}")

        if found == 0:
            return ""

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not fetch pages: {e}")
        return ""


def get_all_canvas_data():
    """Combined function that fetches assignments, announcements, and pages."""
    parts = []

    assignments = get_upcoming_assignments()
    if assignments:
        parts.append(assignments)

    announcements = get_canvas_announcements()
    if announcements:
        parts.append(announcements)

    pages = get_canvas_pages()
    if pages:
        parts.append(pages)

    return "\n\n".join(parts) if parts else "No Canvas data available."


if __name__ == "__main__":
    print("Testing Canvas API connection...")
    print(get_all_canvas_data())

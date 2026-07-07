import asyncio
import logging

logger = logging.getLogger(__name__)

# Track all background tasks for proper cleanup on shutdown
_background_tasks: set[asyncio.Task] = set()

def _track_task(task: asyncio.Task) -> asyncio.Task:
    """Add task to tracking set and auto-remove when done."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

def _cleanup_background_tasks():
    """Cancel any lingering tasks on shutdown to prevent error spam."""
    if _background_tasks:
        logger.info(f"Cancelling {len(_background_tasks)} background tasks...")
        for task in _background_tasks:
            task.cancel()

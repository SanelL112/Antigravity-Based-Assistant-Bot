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

async def cleanup_background_tasks() -> None:
    """Cancel tracked tasks and await their cleanup in application shutdown."""
    tasks = tuple(_background_tasks)
    if not tasks:
        return
    logger.info("Cancelling %d background tasks...", len(tasks))
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def _cleanup_background_tasks() -> None:
    """Synchronous compatibility wrapper; use cleanup_background_tasks in PTB."""
    for task in tuple(_background_tasks):
        task.cancel()

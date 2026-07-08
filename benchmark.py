import asyncio
import time
import os
from unittest.mock import patch, AsyncMock
import scrapers.morning_digest as morning_digest

os.environ["TELEGRAM_BOT_TOKEN"] = "123:test"
os.environ["NOTION_API_KEY"] = "test"
morning_digest.TELEGRAM_BOT_TOKEN = "123:test"
morning_digest.NOTION_API_KEY = "test"

async def background_task():
    start = time.perf_counter()
    # sleep multiple times for very short intervals
    for _ in range(10):
        await asyncio.sleep(0.05)
    return time.perf_counter() - start

async def benchmark_new():
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        # Create a mock response object
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "results": [
                        {
                            "properties": {
                                "Task name": {
                                    "title": [{"text": {"content": f"Task {i}"}}]
                                }
                            }
                        } for i in range(10)
                    ]
                }

        # Simulate network latency (non-blocking)
        async def slow_post(*args, **kwargs):
            await asyncio.sleep(0.5)
            return MockResponse()
        mock_post.side_effect = slow_post

        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None

            # Run both concurrently
            bg_task = asyncio.create_task(background_task())
            digest_task = asyncio.create_task(morning_digest.send_morning_digest())

            bg_time = await bg_task
            await digest_task

            return bg_time

if __name__ == "__main__":
    t = asyncio.run(benchmark_new())
    print(f"Background task took: {t:.4f} seconds (expected ~0.5s if not blocked, >1s if blocked)")

#!/usr/bin/env python3
"""
HTTP server for Orange Pi 5 concurrent classifier.
Receives batch classification requests, processes them with 4 concurrent
qwen2:0.5b workers running on 4 A76 cores.

Endpoints:
    POST /classify  — batch classification (JSON array in, JSON array out)
    GET  /health    — liveness check + model info
    GET  /metrics   — Prometheus-style stats

Start:  python3 pi_classifier_server.py   (listens on 0.0.0.0:8080)
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("pi-classifier")

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2:0.5b"
MAX_CONCURRENT = 4
TIMEOUT = 60

# ── Classification categories ───────────────────────────────────────────────
CATEGORIES = [
    "URGENT",       # deadline today, grade posted, meeting starting
    "HOMEWORK",     # assignment, project due soon
    "ANNOUNCEMENT", # class announcement, schedule change
    "GRADE",        # grade posted, score received
    "MEETING",      # study group, appointment
    "DELIVERY",     # package delivered, mail arrived
    "INFO",         # useful resource, link, reference
    "NOISE",        # spam, memes, jokes, social chat
    "UNSURE",       # can't determine
]

# Partial-match fallbacks for when the model doesn't return an exact category
PARTIAL_MAP = {
    "URGENT":       ["URGENT", "DEADLINE", "IMMEDIATE", "CRITICAL"],
    "HOMEWORK":     ["HOMEWORK", "ASSIGNMENT", "PROJECT", "ESSAY", "DUE"],
    "ANNOUNCEMENT": ["ANNOUNC", "NOTICE", "SCHEDULE", "CANCELLED"],
    "GRADE":        ["GRADE", "SCORE", "FEEDBACK", "GRADED"],
    "MEETING":      ["MEET", "APPOINTMENT", "SESSION"],
    "DELIVERY":     ["DELIVER", "PACKAGE", "SHIPMENT", "TRACKING", "ARRIVED"],
    "INFO":         ["INFO", "RESOURCE", "LINK", "REFERENCE", "MATERIAL"],
    "NOISE":        ["SPAM", "MEME", "JOKE", "LOL", "HAHA", "IRRELEVANT", "CHAT"],
}


# ── Classifier ────────────────────────────────────────────────────────────────
class PiClassifierServer:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: aiohttp.ClientSession | None = None
        self.stats = {
            "total_requests": 0,
            "total_items": 0,
            "by_category": defaultdict(int),
            "by_source": defaultdict(int),
            "errors": 0,
            "start_time": time.time(),
        }

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT, connect=5)
        connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT, limit_per_host=MAX_CONCURRENT
        )
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        # Warm-up so the first real request isn't slow
        try:
            async with self.session.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": "Say hello",
                    "stream": False,
                    "options": {"temperature": 0, "num_predict": 3},
                },
            ) as resp:
                await resp.json()
            logger.info("Model warm-up complete")
        except Exception as e:
            logger.warning(f"Warm-up failed (non-fatal): {e}")

    async def stop(self) -> None:
        if self.session:
            await self.session.close()

    async def classify_one(self, item: dict) -> dict:
        """Classify a single item. Runs under the semaphore for concurrency control."""
        async with self.semaphore:
            start = datetime.now()
            item_id = item.get("id", "?")
            source = item.get("source", "unknown")
            text = item.get("text", "")[:2000]

            cats = ", ".join(CATEGORIES)
            prompt = (
                f"Classify this text. Reply with EXACTLY ONE word: {cats}\n\n"
                f"Text: {text}\n\n"
                "Category:"
            )

            try:
                async with self.session.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0, "num_thread": 1},
                    },
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Ollama HTTP {resp.status}")
                    data = await resp.json()

                response = data.get("response", "").strip().upper()
                latency_ms = int((datetime.now() - start).total_seconds() * 1000)

                # Match response to a category
                classification = self._parse_category(response)
                confidence = 0.9 if classification != "UNSURE" else 0.5

                # Track stats
                self.stats["total_items"] += 1
                self.stats["by_category"][classification] += 1
                self.stats["by_source"][source] += 1

                return {
                    "id": item_id,
                    "source": source,
                    "classification": classification,
                    "confidence": confidence,
                    "tokens": data.get("eval_count", 0),
                    "latency_ms": latency_ms,
                }

            except Exception as e:
                logger.error(f"Classification failed for item {item_id}: {e}")
                self.stats["errors"] += 1
                return {
                    "id": item_id,
                    "source": source,
                    "classification": "ERROR",
                    "confidence": 0.0,
                    "tokens": 0,
                    "latency_ms": int((datetime.now() - start).total_seconds() * 1000),
                    "error": str(e)[:100],
                }

    @staticmethod
    def _parse_category(response: str) -> str:
        """Parse the model's response into a category, with partial-match fallback."""
        # Exact match first
        for cat in CATEGORIES:
            if cat in response:
                return cat

        # Partial match fallback
        for cat, keywords in PARTIAL_MAP.items():
            for kw in keywords:
                if kw in response:
                    return cat

        return "UNSURE"


# ── HTTP Handlers ─────────────────────────────────────────────────────────────
SERVER: PiClassifierServer | None = None


async def classify_handler(request: web.Request) -> web.Response:
    data = await request.json()
    items = data if isinstance(data, list) else [data]

    if SERVER:
        SERVER.stats["total_requests"] += 1

    tasks = [SERVER.classify_one(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    safe_results = []
    for r in results:
        if isinstance(r, dict):
            safe_results.append(r)
        else:
            safe_results.append({"error": str(r)[:200]})

    return web.json_response(safe_results)


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "model": MODEL,
        "workers": MAX_CONCURRENT,
        "categories": CATEGORIES,
        "stats": {
            "total_items": SERVER.stats["total_items"],
            "errors": SERVER.stats["errors"],
            "uptime_seconds": int(time.time() - SERVER.stats["start_time"]),
        } if SERVER else {},
    })


async def metrics_handler(request: web.Request) -> web.Response:
    """Prometheus-style metrics endpoint."""
    if not SERVER:
        return web.Response(text="", content_type="text/plain")

    s = SERVER.stats
    uptime = int(time.time() - s["start_time"])
    lines = [
        f"pi_classifier_total_items {s['total_items']}",
        f"pi_classifier_total_requests {s['total_requests']}",
        f"pi_classifier_errors {s['errors']}",
        f"pi_classifier_uptime_seconds {uptime}",
        f"pi_classifier_workers {MAX_CONCURRENT}",
    ]
    for cat, count in s["by_category"].items():
        lines.append(f'pi_classifier_category_total{{category="{cat}"}} {count}')
    for src, count in s["by_source"].items():
        lines.append(f'pi_classifier_source_total{{source="{src}"}} {count}')

    return web.Response(text="\n".join(lines), content_type="text/plain")


# ── App factory ───────────────────────────────────────────────────────────────
async def create_app() -> web.Application:
    global SERVER
    SERVER = PiClassifierServer()

    app = web.Application()
    app.router.add_post("/classify", classify_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)

    app.on_startup.append(lambda _: SERVER.start())
    app.on_cleanup.append(lambda _: SERVER.stop())
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)

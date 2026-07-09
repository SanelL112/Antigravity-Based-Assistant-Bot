#!/usr/bin/env python3
"""
HTTP server for Orange Pi 5 concurrent classifier.
Receives batch classification requests, processes them with 4 concurrent
qwen2:0.5b workers running on 4 A76 cores.

Endpoint: POST /classify  — batch classification
          GET  /health    — health check

Start:  python3 pi_classifier_server.py   (listens on 0.0.0.0:8080)
"""

import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("pi-classifier")

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2:0.5b"
MAX_CONCURRENT = 4
TIMEOUT = 60


# ── Classifier ────────────────────────────────────────────────────────────────
class PiClassifierServer:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self.stats = {"completed": 0, "failed": 0}

    async def start(self):
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

    async def stop(self):
        if self.session:
            await self.session.close()

    async def classify_one(self, item: dict) -> dict:
        """Classify a single item. Runs under the semaphore for concurrency control."""
        async with self.semaphore:
            start = datetime.now()
            item_id = item.get("id", "?")
            source = item.get("source", "unknown")
            text = item.get("text", "")[:2000]

            prompt = (
                "Classify this message. Reply with EXACTLY ONE word:\n"
                "URGENT = action needed (deadline, grade, meeting)\n"
                "INFO   = useful info (grade, announcement, delivery)\n"
                "NOISE  = spam, memes, irrelevant\n"
                "UNSURE = cannot determine\n\n"
                f"Source: {source}\n"
                f"TEXT: {text}\n\n"
                "ONE WORD:"
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
                tokens = data.get("eval_count", 0)

                # Parse the ONE WORD response
                classification = "UNSURE"
                confidence = 0.5
                for word in ["URGENT", "INFO", "NOISE", "UNSURE"]:
                    if word in response:
                        classification = word
                        confidence = 0.9 if word != "UNSURE" else 0.5
                        break

                self.stats["completed"] += 1
                return {
                    "id": item_id,
                    "source": source,
                    "classification": classification,
                    "confidence": confidence,
                    "tokens": tokens,
                    "latency_ms": latency_ms,
                }

            except Exception as e:
                logger.error(f"Classification failed for item {item_id}: {e}")
                self.stats["failed"] += 1
                return {
                    "id": item_id,
                    "source": source,
                    "classification": "ERROR",
                    "confidence": 0.0,
                    "tokens": 0,
                    "latency_ms": int((datetime.now() - start).total_seconds() * 1000),
                    "error": str(e)[:100],
                }


# ── HTTP Handlers ─────────────────────────────────────────────────────────────
SERVER: PiClassifierServer = None  # set during startup


async def classify_handler(request: web.Request) -> web.Response:
    data = await request.json()
    items = data if isinstance(data, list) else [data]

    tasks = [SERVER.classify_one(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unwrap any exceptions
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
        "stats": SERVER.stats,
    })


# ── App factory ───────────────────────────────────────────────────────────────
async def create_app() -> web.Application:
    global SERVER
    SERVER = PiClassifierServer()

    app = web.Application()
    app.router.add_post("/classify", classify_handler)
    app.router.add_get("/health", health_handler)

    app.on_startup.append(lambda _: SERVER.start())
    app.on_cleanup.append(lambda _: SERVER.stop())
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)

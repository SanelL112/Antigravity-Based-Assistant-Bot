#!/usr/bin/env python3
"""Compatibility entry point for the private, local-only study-guide builder.

The previous script independently loaded dotenv, sent private study material to
cloud providers, wrote into the checkout, and published a Telegram document.
Use ``run_builder`` instead: it keeps the guide in the private export root and
never stages, commits, pushes, or publishes it.
"""
from __future__ import annotations

import logging
import os

from ai_processor import call_agy
from config import (
    MEGA_GUIDE_CLOUD_CLASSIFICATION,
    OPENROUTER_API_KEY,
    OR_FALLBACK_MODEL,
    OR_THIRD_MODEL,
)
from run_builder import main

logger = logging.getLogger(__name__)


def call_guide_model(prompt: str, timeout: int = 3600) -> str:
    """Generate a scheduled mega-guide section with explicit cloud consent."""
    cloud_attempted = False
    if MEGA_GUIDE_CLOUD_CLASSIFICATION == "PUBLIC" and OPENROUTER_API_KEY:
        from llm_router import call_openrouter

        cloud_attempted = True
        result = call_openrouter(
            model=OR_FALLBACK_MODEL,
            prompt=prompt,
            task="mega-guide",
            fallback_chain=[OR_THIRD_MODEL],
            timeout=timeout,
            classification="PUBLIC",
        )
        if result and not result.startswith("⚠️"):
            logger.info("Cloud mega-guide inference succeeded: %s chars", len(result))
            return result
        logger.warning("Cloud mega-guide inference failed; falling back to local inference")

    try:
        result = call_agy(prompt, timeout=timeout, model="flash")
    except Exception as exc:
        logger.warning("Local mega-guide inference failed: %s", type(exc).__name__)
        result = ""

    if result:
        logger.info("Local mega-guide inference succeeded: %s chars", len(result))
        return result
    if cloud_attempted:
        return "❌ Local inference unavailable after approved cloud generation failed."
    return "❌ Local inference unavailable; private mega-guide content was not sent to cloud."


if __name__ == "__main__":
    raise SystemExit(main())

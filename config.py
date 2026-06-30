"""
config.py — Single source of truth for all constants, paths, and configuration.
Import this everywhere instead of hardcoding values.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path("/home/sanel/personal-assistant-bot")
SCRAPERS_DIR = BASE_DIR / "scrapers"
CACHE_DIR = SCRAPERS_DIR / "source_cache"
STUDY_GUIDES_DIR = BASE_DIR / "study_guides"
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
STUDY_DB_DIR = BASE_DIR / "study_database"
ARCHIVE_DIR = BASE_DIR / "offline_archive"

for d in [CACHE_DIR, STUDY_GUIDES_DIR, KNOWLEDGE_BASE_DIR, STUDY_DB_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ── Identity ──────────────────────────────────────────────────────────────────
SANEL_CHAT_ID = 8534649457

# ── API Keys & Tokens ─────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN", "")
GROUPME_ACCESS_TOKEN = os.getenv("GROUPME_ACCESS_TOKEN", "")

# ── External IDs ──────────────────────────────────────────────────────────────
NOTION_DATABASE_ID = "38309c49-e758-8004-8005-c5440093e2cb"
NOTION_OWNER_ID = "2f9d872b-594c-8115-84a6-00028eb47924"
GROUPME_GROUP_ID = "102851186"

# ── agy / Local LLM ──────────────────────────────────────────────────────────
AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")
OLLAMA_URL = "http://localhost:11434"

# ── OpenRouter Models ─────────────────────────────────────────────────────────
OR_FREE_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
]
OR_PAID_MODELS = [
    "openrouter/auto",
]
OR_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
OR_FALLBACK_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

# ── File Paths ────────────────────────────────────────────────────────────────
TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
STATE_FILE = BASE_DIR / "state.json"
LATEST_DIGEST_FILE = BASE_DIR / "latest_digest.txt"
CURATED_BRAIN_FILE = BASE_DIR / "curated_brain.md"
MEGA_INDEX_FILE = BASE_DIR / "mega_index.md"
BOT_CONTEXT_FILE = BASE_DIR / "bot_context.txt"
NIGHTLY_QUEUE_FILE = BASE_DIR / "nightly_queue.json"
COST_LOG_FILE = BASE_DIR / "llm_cost_log.json"
CORRELATION_GRAPH_FILE = BASE_DIR / "correlation_graph.json"
COMBINED_SUMMARIES_FILE = CACHE_DIR / "combined_summaries.txt"
PDF_EXPORTS_FILE = CACHE_DIR / "pdf_exports.txt"
BACKUP_DIR = BASE_DIR / "backups"

# ── Rotation Limits ──────────────────────────────────────────────────────────
MAX_COMBINED_SUMMARIES_CHARS = 50_000      # ~7 days of digests
MAX_MEGA_INDEX_CHARS = 100_000
MAX_CURATED_BRAIN_CHARS = 50_000
MAX_SEEN_TASKS = 200
MAX_CHAT_HISTORY_KB = 50
DIGEST_INTERVAL_SECONDS = 14400            # 4 hours
WATCHDOG_INTERVAL_SECONDS = 1800           # 30 minutes

# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_RETENTION_DAYS = 30
BACKUP_FILES = [
    "state.json", "curated_brain.md", "mega_index.md",
    "bot_context.txt", "latest_digest.txt", "correlation_graph.json",
    "llm_cost_log.json", "nightly_queue.json",
]

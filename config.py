import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the bot directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
SANEL_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))  # Alias for backward compatibility

CONVERSATION_ID = os.getenv("CONVERSATION_ID", "")
SUDO_PASSWORD = os.getenv("SUDO_PASSWORD", "")
GROUPME_TOKEN = os.getenv("GROUPME_TOKEN", "")
GROUPME_GROUP_ID = os.getenv("GROUPME_GROUP_ID", "")

# Validate required environment variables at startup
_missing_vars = []
if not OPENROUTER_API_KEY:
    _missing_vars.append("OPENROUTER_API_KEY")
if not TELEGRAM_BOT_TOKEN:
    _missing_vars.append("TELEGRAM_BOT_TOKEN")
if TELEGRAM_CHAT_ID == 0:
    _missing_vars.append("TELEGRAM_CHAT_ID")
if not CONVERSATION_ID:
    _missing_vars.append("CONVERSATION_ID")

if _missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(_missing_vars)}. Please set them in .env file.")

# ── External Services ─────────────────────────────────────────────────────────
AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")
OLLAMA_URL = "http://localhost:11434"

# ── OpenRouter Models ─────────────────────────────────────────────────────────
OR_DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  # Working, free, 1M context
OR_FALLBACK_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"  # Smaller, free, less rate-limited

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
ARCHIVE_DIR = BASE_DIR / "offline_archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

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
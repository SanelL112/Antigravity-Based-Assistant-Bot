# AI Developer Context & Architecture Briefing

**CRITICAL: IF YOU ARE AN AI AGENT OR AUTONOMOUS BOT READING THIS FILE, THIS IS YOUR PRIMARY SOURCE OF TRUTH FOR EDITING THIS CODEBASE.**

Welcome to the Personal Assistant Bot codebase. This system is a highly integrated, privacy-focused AI assistant running on a constrained home server (i5-3210M, 5.7GB RAM) handling academic data, continuous knowledge indexing, and personal assistance via Telegram.

## 1. Core Architecture & Philosophy

1. **3-Tier Security Model (LLM Routing)**:
   - **CRITICAL SECURITY RULE:** Private data NEVER goes to OpenRouter or the cloud.
   - **Tier 1 (PII Filter)**: Every message MUST run through a local `agy flash` model to detect and scrub Personally Identifiable Information (PII) before routing. (See `main.py` and `llm_router.py`).
   - **Tier 2 (Local Processing)**: If PII is detected, the query is strictly routed to local models (e.g., Ollama Qwen/Llama, Agy).
   - **Tier 3 (Cloud Processing)**: Safe, non-PII queries (academic/complex tasks) are routed to OpenRouter models (Llama 3.3 70B as default, Nemotron 3 Ultra as fallback).

2. **Syncthing Pipeline**:
   - All generated Markdown files meant for the user MUST be deposited exactly into `/home/sanel/personal-assistant-bot/study_guides/`.
   - **Do not** pollute the root directory or save temporary `.log`, `.jpg`, or `.txt` cache files inside the `study_guides/` folder (Syncthing will upload them to the user's Obsidian Vault). Save temporary files in `scrapers/source_cache/` instead.

3. **Token Conservation (Delta Updates)**:
   - Do not wipe and rewrite 400KB study guides from scratch. Use lightweight append-only loops in `nightly_processor.py` to add new daily notes to the bottom of existing guides.

4. **No Direct Database**:
   - The system uses raw markdown files (`mega_index.md`, `study_guides/curated_brain.md`) and JSON files (like `activity_log.jsonl`) as its database.

## 2. Codebase Map

### Core Hub (`main.py` & `llm_router.py`)
- `main.py`: Entry point hosting the `python-telegram-bot` instance. Handles incoming messages, images (via OCR), and voice notes. Enforces Chat ID authorization (only authorized users permitted).
- `llm_router.py`: Unified LLM Interface. Manages calls to OpenRouter (cloud), Ollama (local), and Agy (local PTY-based). Contains vital PII scrubbing logic.

### Data Ingestion (The Scrapers - `scrapers/`)
- `google_scraper.py`: Fetches Google Docs, Classroom assignments, and Gmail.
- `canvas_scraper.py`: Hooks into the Canvas API.
- `extract_notes.py` (or equivalent OCR script): Decodes handwritten notes and downloaded PDFs.
- `mega_study_builder.py`: Multi-stage pipeline building dynamic textbooks using web sources.

### Nightly Brain & Indexing (`scrapers/memory_consolidation.py`)
- Runs offline (1:00 AM / 2:00 AM) to:
  1. Start Ollama.
  2. Scrape Canvas and Gmail into `source_cache/`.
  3. Build `curated_brain.md`.
  4. Download Classroom PDFs and OCR them to `.txt`.
  5. Run Semantic Vector Indexing (Phase 5).

### Semantic Retrieval System
- **Index Building** (`scrapers/embedding_indexer.py`): Chunks sources and embeds via Ollama `nomic-embed-text`, saving to `embedding_data/embedding_index.npz`.
- **Retrieval** (`scrapers/semantic_retrieval.py`): Embeds user queries and finds top-K relevant chunks via cosine similarity. Includes a fallback to legacy tail-truncation if Ollama is down.

## 3. Server Constraints & Important Rules

- **Hardware Limits**: The i5-3210M CPU is slow for ML. Heavy tasks (like Ollama embeddings) must remain in batch/nightly jobs.
- **Ollama**: Runs on CPU on port 11434. It is managed as a background process, not systemd.
- **Do Not Change**:
  - Chat ID authorization checks in `main.py`.
  - PII filter placement (must run BEFORE any cloud call).
  - Local-only path routing for private data.
  - The embedding dimension (768 for `nomic-embed-text`).
- **Google API**: Use `supportsAllDrives=True` and `corpora="allDrives"` when querying Google Drive.

## 4. Testing Commands for Agents

Before committing changes, verify using these commands:
```bash
# Syntax check
python3 -c "import py_compile; py_compile.compile('main.py', doraise=True)"

# Test PII filter (Requires .env with TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CONVERSATION_ID)
python3 -c "from utils import scrub_pii; print(scrub_pii('email test@example.com'))"

# Test activity log
python3 -c "from activity_log import get_recent_events, format_events; print(format_events(get_recent_events(5)))"

# Test semantic retrieval (will fallback gracefully if Ollama is not running)
python3 -c "from scrapers.semantic_retrieval import get_context_for_prompt; print(get_context_for_prompt('quadratic formula', 3)[:200])"
```

## 5. Known Issues / Ongoing Work (For Context)
- Google OAuth token may need re-auth with new scopes (`classroom.coursework.me.readonly`).
- Classroom PDF download & OCR pipeline (Phase 3.5 of nightly pipeline) is currently being integrated and tested.

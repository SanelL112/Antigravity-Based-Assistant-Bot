# Personal Assistant Bot - Architecture Briefing for AI Agents

## Overview
This is a Telegram-based personal assistant bot running on a home server (i5-3210M, 5.7GB RAM). It handles academic data, server management, and general personal assistance.

**Location:** `/home/sanel/personal-assistant-bot/`
**Chat ID:** `8534649457` (Sanel only - unauthorized users get rejected)

---

## Core Architecture

### 1. LLM Routing (3-Tier Security Model)
```
User Message → PII Privacy Filter (agy flash) → Route Decision:
    ├── PII detected → Local only (Ollama Qwen/Llama, agy flash/pro)
    ├── Long/Complex (>300 chars) → OpenRouter Nemotron 3 Ultra (free)
    └── Short/Academic → OpenRouter Llama 3.3 70B (free)
```

**CRITICAL SECURITY RULE:** Private data NEVER goes to OpenRouter/cloud. Only local models (Ollama, agy) handle PII.

### 2. LLM Providers & Models
| Provider | Models | Use Case |
|----------|--------|----------|
| Ollama (local) | nomic-embed-text, Llama3.2:3B, Qwen2.5-Coder:7B, deepseek-coder:6.7b | Embeddings, local chat |
| Agy (local) | flash, pro | PII filter, local coding |
| OpenRouter (cloud) | meta-llama/llama-3.3-70b-instruct:free (default), nvidia/nemotron-3-ultra-550b-a55b:free (fallback) | Academic, long queries |

### 3. Data Sources (All indexed for semantic search)
- `knowledge_base/` - 13 subject guides (math, physics, bio, etc.)
- `study_guides/` - 20+ ACT/SAT study guides (9.7MB, auto-generated)
- `curated_brain.md` - Compressed knowledge base
- `mega_index.md` - Historical data (1MB, capped at 50KB for indexing)
- `scrapers/source_cache/` - Daily digests from Canvas, Gmail, etc.
- `chat_history_*.txt` - Telegram conversation logs
- `classroom_pdfs/` - Downloaded Classroom PDFs (NEW, OCR'd to .txt)

---

## Key Components

### `main.py` - Entry Point & Telegram Handlers
- **Command handlers:** `/help`, `/server`, `/bash`, `/backup`, `/restore`, `/models`, `/summary`, `/ping`, `/stats`, `/correlations`, `/classroom`
- **Message handler:** `handle_message()` - routes through PII filter → LLM
- **Photo handler:** OCR via pytesseract + LLM analysis
- **Voice handler:** Whisper transcription (not yet implemented)
- **PII filter:** Runs `agy flash` on every message before routing

### `llm_router.py` - Unified LLM Interface
- `call_openrouter()` - Cloud calls with PII scrubbing, streaming, fallbacks
- `call_ollama()` - Local Ollama calls
- `call_agy_local()` - Local agy calls (PTY-based)
- `_do_call()` / `_streaming_call()` - Internal OpenRouter execution
- `log_call()` - Cost/latency tracking

### `activity_log.py` - Event Logging
- JSONL format at `activity_log.jsonl`
- Auto-rotates at 5MB (keeps 5000 entries)
- Muted Telegram notifications for important events
- Categories: `message`, `photo`, `llm_call`, `error`, `system`, `scrape`, `nightly`, `mc_server`

### `scrapers/` - Data Collection
| File | Purpose |
|------|---------|
| `google_scraper.py` | Gmail, Classroom, Calendar, Drive, Docs |
| `canvas_scraper.py` | Canvas LMS assignments/grades |
| `memory_consolidation.py` | Nightly pipeline (1 AM) |
| `embedding_indexer.py` | Semantic index building (nomic-embed-text) |
| `semantic_retrieval.py` | Query-time semantic search |
| `compile_context.py` | Legacy tail-truncation (fallback) |
| `nightly_indexer.py` | OpenRouter-based indexing (legacy) |
| `historical_export.py` | Google Takeout processing |

### Nightly Pipeline (1 AM via `memory_consolidation.py`)
1. Start Ollama
2. Scrape Canvas → `source_cache/`
3. Scrape Gmail → `source_cache/`
4. Build curated brain
5. **Download Classroom PDFs + OCR to `.txt`** (Phase 3.5)
6. Run embedding indexer (Phase 5, while Ollama warm)
7. Trim logs

### Semantic Retrieval
- `embedding_indexer.py`: Chunks all sources → embeds via Ollama nomic-embed-text → saves `embedding_index.npz`
- `semantic_retrieval.py`: Query embedding + cosine similarity → top-K chunks
- Fallback: `get_fallback_context()` (old tail-truncation) if Ollama/index unavailable

---

## Telegram Commands
| Command | Purpose |
|---------|---------|
| `/help` | Show all commands |
| `/server` | Full dashboard (RAM, disk, MC, bot, Ollama, services) |
| `/server mc\|bot\|embed\|log\|ram\|services\|start\|stop` | Sub-commands |
|systems |
| `/server log activity [N] [category]` | Activity feed |
| `/bash <cmd>` | Run shell command |
| `/models` | List/switch LLM models |
| `/summary` | Manual data digest |
| `/ping` | Health check |
| `/stats` | Token/cost usage |
| `/correlations` | Cross-source stats |
| `/classroom` | Download Classroom PDFs |
| `/backup` / `/restore` | Brain backups |

---

## Current Known Issues (As of This Session)

### Fixed ✅
- **OpenRouter model deprecated:** `owl-alpha` → replaced with `meta-llama/llama-3.3-70b-instruct:free`
- **Ollama startup:** Fixed `systemctl` calls → direct `ollama serve` / `pkill`
- **Sanity check spam:** Now only runs on suspicious responses (not every message)
- **Flash_lite model:** Replaced with `flash` everywhere
- **Classroom PDF scope:** Added `classroom.coursework.me.readonly` to OAuth

### In Progress / Needs Testing
- **Google OAuth token:** Needs re-auth with new scopes (run `google_auth_setup.py`)
- **Classroom PDF download:** Not yet tested end-to-end (needs valid token)
- **Nightly pipeline Phase 3.5:** Classroom PDF download + OCR not yet run
- **Embedding index:** Built successfully (217 chunks) but not yet tested with Classroom PDFs

---

## Critical Files NOT to Break

### Security-Critical
- `main.py` lines 240-300: PII filter + routing logic
- `llm_router.py` lines 230-240: PII scrubbing before cloud calls
- `config.py`: Model names, API keys

### Core Functionality
- `activity_log.py`: All event tracking
- `scrapers/semantic_retrieval.py`: Query-time search
- `scrapers/embedding_indexer.py`: Index building
- `scrapers/memory_consolidation.py`: Nightly pipeline

---

## Testing Commands
```bash
# Syntax check
cd ~/personal-assistant-bot && source venv/bin/activate && python3 -c "import py_compile; py_compile.compile('main.py', doraise=True)"

# Test semantic retrieval
python3 -c "from scrapers.semantic_retrieval import get_context_for_prompt; print(get_context_for_prompt('quadratic formula', 3)[:200])"

# Test activity log
python3 -c "from activity_log import get_recent_events, format_events; print(format_events(get_recent_events(5)))"

# Test PII filter
python3 -c "from utils import scrub_pii; print(scrub_pii('email test@example.com'))"

# Restart bot
sudo systemctl restart bot.service
```

---

## DO NOT CHANGE
- Chat ID authorization (line 31 in config, checks in main.py)
- PII filter placement (must run BEFORE any cloud call)
- Local-only path for private data
- Embedding dimension (768, nomic-embed-text)
- File paths in config.py

---

## Git Workflow
- All changes committed to `main` branch
- Push to `https://github.com/SanelL112/Antigravity-Based-Assistant-Bot.git`
- Format: `git add -A && git commit -m "..." && git push origin main`

---

## Server Constraints
- **CPU:** i5-3210M (2 cores, 4 threads, 2.5GHz) - very slow for ML
- **RAM:** 5.7GB total, MC server uses ~1.5GB
- **Ollama:** Runs on CPU, embedding ~5 min/batch of 4 chunks
- **Ollama port:** 11434 (NOT systemd, runs as background process)

---

## Questions? 
Ask before making architectural changes. Small fixes are fine but routing logic, PII handling, or model selection changes need review.
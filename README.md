# Personal Assistant Bot (Local AI Ecosystem)

Welcome to the Personal Assistant Bot! This is a highly integrated, intelligent Telegram bot designed to act as an autonomous ecosystem for a home server environment. It seamlessly manages academic data, serves as a continuous knowledge indexer, tracks your tasks, and provides robust personal assistance directly through Telegram.

## Core Features

- **Telegram Interface**: Interact natively through Telegram. Ask questions, run commands, upload images for OCR and homework help, send voice messages for transcription, and receive scheduled digests.
- **3-Tier Security Model for LLM Routing**: A strict privacy-first pipeline ensures your sensitive personal data is protected:
  - **PII Filter**: Every message is scanned by a local `agy flash` model to detect Personally Identifiable Information (PII).
  - **Local Processing**: Any message containing PII is strictly routed to local LLMs (e.g., Ollama Qwen/Llama, Agy) and never touches the cloud.
  - **Cloud Processing (OpenRouter)**: Safe, non-sensitive complex queries or academic tasks are routed to OpenRouter models (like Llama 3.3 70B or Nemotron 3 Ultra) for powerful reasoning.
- **Semantic Retrieval System**: Uses local Ollama (`nomic-embed-text`) to build a semantic vector index from all your knowledge sources (study guides, historical data, classroom PDFs). At query time, the bot retrieves the most relevant context using cosine similarity, giving it a deep "memory" of your specific content.
- **Continuous Knowledge Indexing**: Automatically scrapes data from Canvas LMS, Google Classroom, Google Docs, Gmail, and GroupMe. It downloads Classroom PDFs and OCRs handwritten notes to weave them into your overall knowledge base.
- **Task Tracking (Notion Integration)**: Automatically detects new assignments from Canvas and Classroom and syncs them to your Notion Task Tracker database. You can reply directly in Telegram to set priorities or update task status.
- **Syncthing & Obsidian Integration**: Completely integrated with Syncthing. All generated master study guides and knowledge logs are explicitly saved into a dedicated `study_guides/` folder, which syncs directly into your local Obsidian Vault.
- **Nightly Delta-Updates**: Every night at 1:00 AM, the bot runs a pipeline to append new knowledge and daily school topics to your existing massive `.md` textbooks. This append-only "delta" logic prevents token waste and avoids rebuilding huge guides from scratch.

## Setup Instructions

### 1. Prerequisites
- **Python 3.10+**
- **System Dependencies**: Tesseract OCR (`sudo apt install tesseract-ocr`) and FFmpeg (for voice processing).
- **Ollama**: Must be installed and running in the background (typically on port `11434`). Required models include `nomic-embed-text`.
- **Syncthing**: Configured to point to your `study_guides/` directory to sync with Obsidian.
- **whisper.cpp** or **openai-whisper**: (Optional but recommended) For local voice transcription.

### 2. Environment Variables
Create a `.env` file in the root directory with the following keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id  # Restricts the bot to only you
OPENROUTER_API_KEY=your_openrouter_token
CANVAS_API_URL=https://canvas.instructure.com
CANVAS_API_TOKEN=your_canvas_token
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
GROUPME_ACCESS_TOKEN=your_groupme_token
GROUPME_GROUP_ID=your_groupme_group_id
```

### 3. Google API Credentials
Place your `credentials.json` (from Google Cloud Console) in the root directory. Run the bot or `scrapers/google_auth_setup.py` once to generate a `token.json` file for Google Workspace integration (Classroom, Drive, Gmail).

### 4. Running the Bot
The bot is designed to run continuously on a server, typically managed as a systemd service (`bot.service`). Ensure Ollama is running in the background for embedding and local queries.
```bash
python3 main.py
```

## Available Telegram Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands. |
| `/server` | Open the full dashboard (RAM, disk, MC Server, Bot status, Ollama). |
| `/server <subcommand>` | Run subcommands like `start`/`stop` for the MC Server, or view `log` and `ram`. |
| `/bash <cmd>` | Run a shell command directly on the host server. |
| `/models` | List or switch the active LLM models for routing. |
| `/summary` | Generate a manual data digest from all your connected sources. |
| `/ping` | Health check for the bot and server. |
| `/stats` | View token usage and cost statistics. |
| `/correlations` | View cross-source semantic correlations. |
| `/classroom` | Force a manual download and OCR of recent Classroom PDFs. |
| `/backup` / `/restore`| Manage backups of the bot's knowledge brain. |

## Server Constraints & Considerations

- **Hardware**: Designed for a home server environment (e.g., older i5 CPU, ~6GB RAM). Heavy ML tasks (like embedding with Ollama) are run on the CPU and may take time, which is why intensive tasks are scheduled as nightly batch jobs.
- **Data Privacy**: The local routing logic in `main.py` and `llm_router.py` must remain intact to prevent accidental PII leakage to cloud providers.
- **Syncthing Pipeline**: Temporary files or cache data must be saved to `scrapers/source_cache/` rather than `study_guides/` to prevent cluttering your Obsidian Vault.

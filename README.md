# Personal Assistant Bot (Local AI Ecosystem)

Welcome to the Personal Assistant Bot! This is a highly integrated, privacy-focused AI assistant built with Python, Telegram, and a local **Llama 3.2** model running via Ollama. 

Unlike traditional chatbots, this assistant acts as an autonomous ecosystem that continuously scrapes, indexes, and monitors your digital life to provide proactive assistance, study guides, and daily digests.

## Core Features

- **Telegram Interface**: Interact with the bot natively through Telegram. Ask questions, upload images (for OCR/homework help), and receive push notifications.
- **Local AI Processing**: Uses a local `llama3.2` model (via Ollama) to process all data. No data is sent to external LLM providers like OpenAI, ensuring total privacy.
- **Continuous Knowledge Indexing**: 
  - Automatically scrapes Google Classroom (announcements, assignments, PDFs), Canvas, Google Docs, and Gmail.
  - Builds an append-only timeline (`curated_brain.md`) and a summarized knowledge graph (`mega_index.md`).
- **Morning Digest**: Sends a scheduled daily briefing (7:00 AM ET) summarizing upcoming assignments, unread emails, and events.
- **Notion Watchdog**: Automatically pushes new assignments and tasks to a Notion database and asks for status updates.
- **Study Guide Generation**: Can instantly generate comprehensive study guides using your uploaded coursework, past assignments, and PDF readings.

## Architecture & Ecosystem

The system is broken down into several asynchronous pipelines:

1. **The Telegram Bot (`main.py`)**: The central hub that receives messages, handles OCR for images, and responds to queries by injecting the latest knowledge index into its system prompt.
2. **The Scrapers (`scrapers/`)**: 
   - `google_scraper.py`: Fetches Drive documents, Gmail, and Classroom data.
   - `canvas_scraper.py`: Fetches Canvas assignments and pages.
   - `historical_export.py`: Performs massive one-time scrapes of historical data.
3. **The Indexers (`scrapers/nightly_indexer.py` & `memory_consolidation.py`)**: Runs offline to chunk massive amounts of text, feed them into the local Llama model, and extract actionable insights into the `mega_index.md` and `curated_brain.md`.
4. **Context Injection (`scrapers/compile_context.py`)**: Compresses the massive knowledge bases into a tight, optimized `bot_context.txt` that is fed into the Telegram bot's real-time prompt.

## Setup Instructions

1. **Requirements**:
   - Python 3.10+
   - `ollama` running locally with `llama3.2` installed (`ollama run llama3.2`)
   - Tesseract OCR (`sudo apt install tesseract-ocr`)
2. **Environment Variables (`.env`)**:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   CANVAS_API_URL=https://canvas.instructure.com
   CANVAS_API_TOKEN=your_canvas_token
   NOTION_TOKEN=your_notion_integration_token
   NOTION_DATABASE_ID=your_notion_database_id
   ```
3. **Google API Credentials**:
   Place your `credentials.json` in the root directory. On first run, the bot will generate a `token.json` file for Google Drive, Classroom, and Gmail access.
4. **Running the Bot**:
   The bot is designed to run continuously as a systemd service (`bot.service`).
   ```bash
   python3 main.py
   ```

## Background Jobs

The bot natively schedules the following tasks:
- `02:00 AM`: Runs memory consolidation, downloads new Classroom PDFs, and rebuilds the AI context.
- `07:00 AM`: Generates and sends the Morning Digest.
- `Every 30 Mins`: Runs the Watchdog to check for new Notion tasks and assignments.

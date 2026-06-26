# Personal Assistant Bot (Local AI Ecosystem)

Welcome to the Personal Assistant Bot! This is a highly integrated AI assistant that acts as an autonomous ecosystem. It continuously scrapes, indexes, and monitors your digital life to provide proactive assistance, massive study guides, and daily digests.

## Core Features

- **Telegram Interface**: Interact with the bot natively through Telegram. Ask questions, upload images (for OCR/homework help), and receive push notifications.
- **OpenRouter & Hybrid Processing**: Uses OpenRouter (Owl-Alpha / Flash) for incredibly powerful reasoning and multi-stage document generation, with local processing fallbacks.
- **Syncthing & Obsidian Integration**: Completely integrated with Syncthing. All generated master study guides and brain logs are strictly deposited into an isolated `study_guides/` folder that magically beams directly into your local Obsidian Vault.
- **Continuous Knowledge Indexing**: 
  - Automatically scrapes Google Classroom, Canvas, Google Docs, and Gmail.
  - OCRs handwritten notes and automatically weaves them into your existing study guides.
- **Nightly Delta-Update Generation**: Scrapes daily school notes and uses lightweight AI calls to append new knowledge to existing massive `.md` textbooks without wasting tokens rebuilding them from scratch.
- **Morning Digest**: Sends a scheduled daily briefing (7:00 AM ET) summarizing upcoming assignments, unread emails, and events.

## Architecture & Ecosystem

The system is broken down into several asynchronous pipelines:

1. **The Telegram Bot (`main.py`)**: The central hub that receives messages, handles OCR, and responds to queries.
2. **The Scrapers (`scrapers/`)**: 
   - `google_scraper.py` & `canvas_scraper.py`: Fetches documents, assignments, and announcements.
   - `extract_notes.py`: The OCR pipeline for decoding handwritten math and theory.
3. **The Nightly Brain (`nightly_processor.py` & `overnight_researcher.py`)**: Runs offline to chunk massive amounts of text, extract dynamic school topics you learned that day, and inject them into `curated_brain.md` and the SAT Master Guides.
4. **Mega Study Builder (`mega_study_builder.py`)**: A sprawling 10-chapter Editor-in-Chief pipeline that builds 50-page textbooks dynamically by searching DuckDuckGo and YouTube transcripts.

## Setup Instructions

1. **Requirements**:
   - Python 3.10+
   - Tesseract OCR (`sudo apt install tesseract-ocr`)
   - Syncthing configured to point to `/home/sanel/personal-assistant-bot/study_guides/`
2. **Environment Variables (`.env`)**:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENROUTER_API_KEY=your_openrouter_token
   CANVAS_API_URL=https://canvas.instructure.com
   CANVAS_API_TOKEN=your_canvas_token
   ```
3. **Google API Credentials**:
   Place your `credentials.json` in the root directory to generate a `token.json` file.
4. **Running the Bot**:
   The bot is designed to run continuously as a systemd service (`bot.service`).

## Background Jobs

- `Midnight/2:00 AM`: Runs memory consolidation, downloads new Classroom PDFs, OCRs them, and executes the delta-append logic to upgrade the `study_guides/` folder.
- `07:00 AM`: Generates and sends the Morning Digest to Telegram.

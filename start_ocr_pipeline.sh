#!/bin/bash
cd /home/sanel/personal-assistant-bot

echo "Starting historical export (Tesseract OCR) at $(date)..."
/home/sanel/personal-assistant-bot/venv/bin/python scrapers/historical_export.py

echo "Starting mega study guide builder at $(date)..."
/home/sanel/personal-assistant-bot/venv/bin/python run_builder.py

echo "Pushing changes to GitHub at $(date)..."
git add SAT_Study_Guide.md SAT_Study_Guide.docx
git commit -m "feat: Include missing Tesseract OCR PDFs in SAT guide"
git push

echo "All done!"

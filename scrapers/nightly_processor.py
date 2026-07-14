import os
import json
import logging
import asyncio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def run_nightly_job(bot, chat_id):
    queue_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nightly_queue.json")
    if not os.path.exists(queue_path):
        return
        
    with open(queue_path, "r") as f:
        queue = json.load(f)
        
    if not queue:
        return
        
    logger.info(f"Running nightly processing on {len(queue)} files...")
    
    import tempfile
    from scrapers.google_scraper import download_drive_file
    import PyPDF2
    import httpx
    
    successful = []
    
    for item in queue:
        title = item['title']
        file_id = item['file_id']
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
            
        if download_drive_file(file_id, path):
            try:
                reader = PyPDF2.PdfReader(path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                    
                if len(text.strip()) <= 50:
                    try:
                        import pytesseract
                        from pdf2image import convert_from_path
                        logger.info(f"Running nightly OCR on {title}...")
                        images = convert_from_path(path)
                        text = ""
                        for img in images:
                            text += pytesseract.image_to_string(img) + "\n"
                    except Exception as e:
                        logger.error(f"Failed OCR on {title}: {e}")
                
                if len(text.strip()) > 50:
                    # Export the extracted PDF text to the massive memory bank instead of sending a Telegram message
                    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "pdf_exports.txt")
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(f"\n\n=== EXPORTED PDF: {title} ===\n")
                        f.write(text)
                        
                    logger.info(f"Successfully exported {title} to text file.")
                    successful.append(item)
            except Exception as e:
                logger.error(f"Failed to process PDF {title}: {e}")
                
        try:
            os.remove(path)
        except Exception:
            pass
            
    # Forcefully clear the queue so we don't infinitely retry broken/un-downloadable PDFs every single night
    with open(queue_path, "w") as f:
        json.dump([], f)
    
if __name__ == "__main__":
    import sys
    # For testing manually
    from telegram import Bot
    from config import SANEL_CHAT_ID
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_BOT_TOKEN:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        asyncio.run(run_nightly_job(bot, SANEL_CHAT_ID))

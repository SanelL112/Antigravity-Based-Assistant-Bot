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
                    
                if len(text.strip()) > 50:
                    prompt = (
                        "You are an academic tutor. Read the following text extracted from a practice worksheet or homework assignment.\n"
                        "Generate 3 challenging practice questions based on the concepts covered in the material.\n"
                        "At the very bottom, provide the answer key.\n\n"
                        f"MATERIAL ({title}):\n{text[:15000]}"
                    )
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "http://localhost:11434/api/generate",
                            json={
                                "model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest",
                                "prompt": prompt,
                                "stream": False
                            },
                            timeout=300.0
                        )
                    
                    if response.status_code == 200:
                        gen_text = response.json().get("response", "").strip()
                        msg = f"🌙 **Nightly Local Processing: {title}**\n\n{gen_text}"
                        try:
                            await bot.send_message(chat_id=chat_id, text=msg, disable_notification=True, parse_mode="Markdown")
                        except Exception:
                            await bot.send_message(chat_id=chat_id, text=msg, disable_notification=True)
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
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    SANEL_CHAT_ID = 8534649457
    if TELEGRAM_BOT_TOKEN:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        asyncio.run(run_nightly_job(bot, SANEL_CHAT_ID))

import os
import json
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "..", "offline_archive")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "mega_index.md")

def chunk_text(text, chunk_size=8000):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]

async def process_chunk(chunk, chunk_index, source_name, max_retries=3):
    prompt = (
        "You are a highly meticulous academic data curator. Read the following chunk of raw data extracted from the student's learning platforms.\n"
        "You MUST provide an EXHAUSTIVE index of EVERY SINGLE file, document, announcement, and assignment found in this chunk. DO NOT ignore or skip anything, regardless of whether you think it is important or not.\n"
        "For each item, extract and output the following points clearly:\n"
        "1. EXACT TITLE/NAME of the file or item.\n"
        "2. What information is contained in it.\n"
        "3. How this information could be useful for study guides.\n"
        "4. What this reveals about what the student is doing or learning.\n\n"
        f"SOURCE: {source_name}\n"
        f"DATA:\n{chunk}"
    )
    
    for attempt in range(max_retries):
        try:
            import httpx
            import os
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                from dotenv import load_dotenv
                load_dotenv("/home/sanel/personal-assistant-bot/.env")
                api_key = os.getenv("OPENROUTER_API_KEY")
                
            async with httpx.AsyncClient(timeout=3600.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com/SanelL112/Antigravity-Based-Assistant-Bot",
                        "X-Title": "Antigravity-Based-Assistant-Bot"
                    },
                    json={
                        "models": ["openrouter/owl-alpha:free", "openrouter/owl-alpha"],
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"OpenRouter returned {response.status_code}. Retrying...")
                    await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error communicating with OpenRouter: {e}")
            await asyncio.sleep(5)
    return None

async def run_indexing():
    logger.info("Starting Massive Historical Indexing...")
    delta_file = os.path.join(ARCHIVE_DIR, "delta_export.txt")
    if not os.path.exists(delta_file):
        logger.info("No delta file found. Nothing to index.")
        return
        
    try:
        with open(delta_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Failed to read delta_export.txt: {e}")
        return
        
    if not text.strip():
        logger.info("Delta file empty.")
        return
        
    chunks = list(chunk_text(text, chunk_size=8000))
    total_chunks = len(chunks)
    
    success_count = 0
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{total_chunks} for delta_export...")
        result = await process_chunk(chunk, i+1, "delta_export")
        if result:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
                out_f.write(f"\n\n## Source: Nightly Delta (Part {i+1}/{total_chunks})\n\n")
                out_f.write(result)
            success_count += 1
                
    if success_count == total_chunks:
        open(delta_file, 'w').close()
        logger.info("Delta Indexing Complete. Output appended to mega_index.md.")
    else:
        logger.warning(f"Only {success_count}/{total_chunks} chunks were indexed. Delta file was NOT cleared to prevent data loss.")

if __name__ == "__main__":
    asyncio.run(run_indexing())

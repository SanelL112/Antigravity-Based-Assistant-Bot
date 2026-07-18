import os
import json
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "..", "offline_archive")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "mega_index.md")

def chunk_text(text, chunk_size=8000):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]

async def process_chunk(chunk, chunk_index, source_name, max_retries=2):
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
    
    # Route through the unified local-inference chain (Surface llama-server
    # at 10.0.0.47:8080, then Pi Ollama). This replaces the old hardcoded
    # localhost:11434 call that required a model that was never pulled here.
    from llm_router import call_local_rpc

    for attempt in range(max_retries):
        try:
            result = await asyncio.to_thread(
                call_local_rpc,
                prompt=prompt,
                max_tokens=2048,
                temperature=0.1,
                timeout=120,
            )
            if result and result.strip():
                return result
            # Empty means all local paths (Surface + Pi) are down — don't retry.
            logger.warning("Local inference unavailable. Skipping offline indexing.")
            return None
        except Exception as e:
            logger.error(f"Error during local inference: {e}. Retrying ({attempt+1}/{max_retries})...")
            await asyncio.sleep(5)

    logger.warning(f"Local indexing failed after {max_retries} attempts")
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
    local_inference_down = False
    for i, chunk in enumerate(chunks):
        # Circuit breaker: if local inference is down, stop hammering it. Emit a
        # single summary line instead of one misleading warning per chunk.
        if local_inference_down:
            continue

        logger.info(f"Processing chunk {i+1}/{total_chunks} for delta_export...")
        result = await process_chunk(chunk, i+1, "delta_export")
        if result:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
                out_f.write(f"\n\n## Source: Nightly Delta (Part {i+1}/{total_chunks})\n\n")
                out_f.write(result)
            success_count += 1
        elif i == 0:
            # First chunk failed — the whole local-inference chain (Surface
            # llama-server + Pi fallback) is unavailable. Circuit-break so we
            # don't retry 174 more times and spam Telegram.
            local_inference_down = True
            skipped = total_chunks - 1
            logger.warning(
                f"Local inference (Surface RPC + Pi) unavailable — skipping "
                f"{skipped} remaining chunk(s). Delta preserved for next run."
            )
                
    if success_count == total_chunks:
        open(delta_file, 'w').close()
        logger.info("Delta Indexing Complete. Output appended to mega_index.md.")
    else:
        logger.warning(f"Only {success_count}/{total_chunks} chunks were indexed. Delta file was NOT cleared to prevent data loss.")

if __name__ == "__main__":
    asyncio.run(run_indexing())

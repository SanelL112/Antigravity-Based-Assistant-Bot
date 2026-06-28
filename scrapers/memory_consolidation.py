import os
import glob
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
import asyncio
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def consolidate_memory():
    import subprocess
    logger.info("Starting 1 AM Pipeline: Preparing system for heavy local AI processing...")
    try:
        # Start Ollama
        subprocess.run('echo "Forgot@2023" | sudo -S systemctl start ollama', shell=True, check=False)
        logger.info("System prepared successfully.")
    except Exception as e:
        logger.error(f"Failed to prepare system: {e}")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_cache_dir = os.path.join(base_dir, "scrapers", "source_cache")
    
    # Gather raw text
    raw_text = ""
    
    # 1. Read combined_summaries.txt
    summaries_file = os.path.join(source_cache_dir, "combined_summaries.txt")
    if os.path.exists(summaries_file):
        with open(summaries_file, "r") as f:
            raw_text += "\n--- DAILY SUMMARIES AND NOTES ---\n" + f.read()
            
    # 2. Read chat_history files
    chat_files = glob.glob(os.path.join(base_dir, "chat_history_*.txt"))
    for cf in chat_files:
        with open(cf, "r") as f:
            raw_text += f"\n--- CHAT HISTORY ({os.path.basename(cf)}) ---\n" + f.read()
            
    if not raw_text.strip():
        logger.info("No raw memory to consolidate tonight.")
        return
        
    logger.info("Consolidating memory via Llama 3 8B...")
    prompt = (
        "You are the central Memory Consolidation Engine. It is 2:00 AM. Your task is to process the following raw, messy logs from the day "
        "(including scraped assignments, chat history, and auto-transcribed handwritten notes) and compress them into a pristine, beautifully organized 'curated brain' document.\n\n"
        "Format your output in Markdown with the following sections:\n"
        "- **Upcoming Deadlines & Tasks**\n"
        "- **Current Study Topics** (What is the user currently learning based on their notes? Be specific.)\n"
        "- **Key Insights** (Important things to remember, group drama, or overarching themes).\n\n"
        "Discard all redundant greetings, boilerplate text, and irrelevant chatter. Be concise.\n\n"
        f"RAW DATA:\n{raw_text[:20000]}"
    )
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2
                    }
                },
                timeout=7200.0 # Heavy generation could take up to 2 hours on CPU
            )
            
        if response.status_code == 200:
            brain = response.json().get("response", "").strip()
        else:
            raise Exception(f"Ollama returned {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Local Llama 3.2 failed to consolidate memory ({e}). Falling back to secure local G1 Flash to protect PII...")
        from ai_processor import call_agy
        brain = call_agy(prompt, timeout=180, model="flash")

    if not brain:
        logger.error("All local models failed to consolidate memory. Aborting to protect PII.")
        return

    # Phase 1: Write brain to file
    try:
        brain_file = os.path.join(base_dir, "curated_brain.md")
        existing_brain = ""
        if os.path.exists(brain_file):
            with open(brain_file, "r") as f:
                existing_brain = f.read()
        
        final_brain = brain
        if existing_brain:
            # Merge old and new
            merge_prompt = f"Merge the old brain and new daily insights into a single cohesive document.\n\nOLD BRAIN:\n{existing_brain}\n\nNEW INSIGHTS:\n{brain}"
            try:
                async with httpx.AsyncClient() as client:
                    resp2 = await client.post("http://localhost:11434/api/generate", json={"model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest", "prompt": merge_prompt, "stream": False}, timeout=7200.0)
                    if resp2.status_code == 200:
                        final_brain = resp2.json().get("response", "").strip()
                    else:
                        raise Exception("Ollama merge failed")
            except Exception as e:
                logger.warning(f"Local Llama 3.2 failed to merge brain ({e}). Falling back to secure local G1 Flash...")
                from ai_processor import call_agy
                merged = call_agy(merge_prompt, timeout=180, model="flash")
                if merged: final_brain = merged
                    
        with open(brain_file, "w") as f:
            f.write(final_brain)
    except Exception as e:
        logger.error(f"Failed to write brain file: {e}")
            
    # Phase 2: Trigger Deep-Dive Online Researcher
    logger.info("Triggering offline topic researcher...")
    try:
        import subprocess
        subprocess.run(["python3", os.path.join(base_dir, "overnight_researcher.py")], timeout=1800)
    except Exception as e:
        logger.error(f"Overnight researcher failed: {e}")
            
    # Phase 3: Massive Historical Indexing
    logger.info("Running massive historical data export...")
    try:
        from scrapers.historical_export import run_all_exports
        run_all_exports()
    except Exception as e:
        logger.error(f"Historical export failed: {e}")
            
    # Phase 4: Nightly Indexer
    logger.info("Running nightly massive indexer via OpenRouter...")
    try:
        from scrapers.offline_indexer import run_indexing
        await run_indexing()
    except Exception as e:
        logger.error(f"Nightly indexer failed: {e}")
            
    logger.info("Daily pipeline complete.")

    # Phase 5: Wipe raw logs (always attempt, even if earlier phases failed)
    try:
        if os.path.exists(summaries_file):
            os.remove(summaries_file)
        for cf in chat_files:
            os.remove(cf)
        logger.info("Memory consolidation complete! Raw logs wiped.")
    except Exception as e:
        logger.error(f"Failed to wipe raw logs: {e}")

if __name__ == "__main__":
    asyncio.run(consolidate_memory())

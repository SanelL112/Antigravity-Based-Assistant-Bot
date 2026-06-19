import os
import glob
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def consolidate_memory():
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2
                    }
                },
                timeout=600.0 # Heavy generation could take up to 10 minutes on CPU
            )
            
        if response.status_code == 200:
            brain = response.json().get("response", "").strip()
            
            brain_file = os.path.join(base_dir, "curated_brain.md")
            # If the file already exists, we should merge them, but for now we'll just rewrite it
            # Actually, let's prepend yesterday's brain
            existing_brain = ""
            if os.path.exists(brain_file):
                with open(brain_file, "r") as f:
                    existing_brain = f.read()
            
            final_brain = brain
            if existing_brain:
                # Merge old and new
                merge_prompt = f"Merge the old brain and new daily insights into a single cohesive document.\n\nOLD BRAIN:\n{existing_brain}\n\nNEW INSIGHTS:\n{brain}"
                async with httpx.AsyncClient() as client:
                    resp2 = await client.post("http://localhost:11434/api/generate", json={"model": "llama3:latest", "prompt": merge_prompt, "stream": False}, timeout=600.0)
                    if resp2.status_code == 200:
                        final_brain = resp2.json().get("response", "").strip()
                        
            with open(brain_file, "w") as f:
                f.write(final_brain)
                
            # WIPE RAW LOGS
            if os.path.exists(summaries_file):
                os.remove(summaries_file)
            for cf in chat_files:
                os.remove(cf)
                
            logger.info("Memory consolidation complete! Raw logs wiped.")
            
    except Exception as e:
        logger.error(f"Failed to consolidate memory: {e}")

if __name__ == "__main__":
    asyncio.run(consolidate_memory())

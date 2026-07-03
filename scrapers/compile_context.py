import os
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def compile_bot_context():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    curated_brain_path = os.path.join(base_dir, "curated_brain.md")
    mega_index_path = os.path.join(base_dir, "mega_index.md")
    
    brain_content = ""
    if os.path.exists(curated_brain_path):
        with open(curated_brain_path, "r", encoding="utf-8") as f:
            # Get the last 15,000 chars of the curated brain (recent days)
            content = f.read()
            brain_content = content[-15000:] if len(content) > 15000 else content
            
    mega_index_content = ""
    if os.path.exists(mega_index_path):
        with open(mega_index_path, "r", encoding="utf-8") as f:
            # Get the last 10,000 chars of the mega index (recent assignments)
            content = f.read()
            mega_index_content = content[-10000:] if len(content) > 10000 else content
            
    if not brain_content and not mega_index_content:
        logger.info("No memory files found to compile.")
        return
        
    prompt = (
        "You are generating the core System Prompt Context for a Telegram Personal Assistant Bot.\n"
        "Read the following recent excerpts from the user's Curated Brain (short-term memory) and Mega Index (long-term memory).\n"
        "Your job is to compress this information into a dense, highly concise 2-paragraph summary of EXACTLY what the user's current life state is. "
        "List the active classes they are taking, the current overarching topics they are studying, any group drama, and any active deadlines.\n\n"
        "Output ONLY the raw compressed context. Do not add conversational filler.\n\n"
        f"--- RECENT CURATED BRAIN ---\n{brain_content}\n\n"
        f"--- RECENT MEGA INDEX ---\n{mega_index_content}"
    )
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=300.0
            )
            
        if response.status_code == 200:
            context_str = response.json().get("response", "").strip()
            
            out_file = os.path.join(base_dir, "bot_context.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(context_str)
            logger.info("Successfully compiled bot_context.txt")
        else:
            logger.error(f"Failed to generate context, status {response.status_code}")
    except Exception as e:
        logger.error(f"Error compiling context: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(compile_bot_context())

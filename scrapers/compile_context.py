import os
import httpx
import logging

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
    
    # Route through the unified local-inference chain (Surface llama-server
    # at 10.0.0.47:8080, then Pi Ollama) instead of the old hardcoded
    # localhost:11434 model that was never pulled here.
    import asyncio
    from llm_router import call_local_rpc
    try:
        context_str = await asyncio.to_thread(
            call_local_rpc,
            prompt=prompt,
            max_tokens=1024,
            temperature=0.1,
            timeout=300,
            classification="PRIVATE",
        )
        if context_str and context_str.strip():
            out_file = os.path.join(base_dir, "bot_context.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(context_str.strip())
            logger.info("Successfully compiled bot_context.txt")
        else:
            logger.info("Local inference unavailable (Surface + Pi) — skipping context compilation")
    except Exception as e:
        logger.error(f"Error compiling context: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(compile_bot_context())

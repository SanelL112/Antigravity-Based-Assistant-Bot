import os
import json
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
import asyncio
import httpx
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import config for fallback models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OR_FALLBACK_MODEL

async def pre_cache_web():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brain_file = os.path.join(base_dir, "curated_brain.md")
    
    if not os.path.exists(brain_file):
        logger.info("No curated brain found. Skipping web pre-caching.")
        return
        
    with open(brain_file, "r") as f:
        brain = f.read()
        
    # 1. Ask local model what topics we should research
    logger.info("Asking local model to identify research topics...")
    prompt = (
        "Based on the following curated brain of a student, identify ONE specific academic topic they are currently learning that would benefit from extra web research (e.g., 'Quadratic Formula', 'Cellular Respiration').\n"
        "Reply with ONLY the topic name. If there are no academic topics, reply with 'NONE'.\n\n"
        f"BRAIN:\n{brain}"
    )
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("No OPENROUTER_API_KEY found, aborting web precache.")
            return

        from llm_router import call_openrouter
        def _call_or(m_name, prompt_text):
            try:
                return call_openrouter(model=m_name, prompt=prompt_text, task="web-precache", timeout=120)
            except Exception:
                return None
                
        topic = await _call_or("nvidia/nemotron-3-ultra-550b-a55b:free", prompt)
        if not topic or any(p in topic.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai"]):
            logger.warning(f"Nemotron failed in precacher, falling back to {OR_FALLBACK_MODEL}...")
            fallback = await _call_or(OR_FALLBACK_MODEL, prompt)
            if fallback and not any(p in fallback.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai"]):
                topic = fallback
            else:
                logger.warning("Fallback failed, falling back to local G1 Flash...")
                from ai_processor import call_agy
                topic = call_agy(prompt, timeout=120, model="flash")
            
        if not topic: topic = ""
        topic = re.sub(r'[^a-zA-Z0-9\s]', '', topic)
        
        if not topic or "NONE" in topic.upper() or len(topic) > 50:
            logger.info("No valid topics found to research.")
            return
            
        logger.info(f"Identified topic for pre-caching: {topic}")
        
        # 2. Search the web (using a simple DuckDuckGo HTML scrape)
        from urllib.parse import quote_plus
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(topic + ' explanation examples')}"
        
        async with httpx.AsyncClient() as client:
            res = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all('a', class_='result__snippet', limit=3)
        urls_to_scrape = [a['href'] for a in results if 'href' in a.attrs]
        
        if not urls_to_scrape:
            logger.warning("No search results found.")
            return
            
        # 3. Scrape the sites and summarize
        combined_research = ""
        for url in urls_to_scrape:
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    page_res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
                page_soup = BeautifulSoup(page_res.text, "html.parser")
                text = " ".join([p.text for p in page_soup.find_all('p')])
                
                # Summarize
                sum_prompt = f"Summarize the following educational text about {topic}. Extract key formulas, facts, and examples.\n\nTEXT:\n{text[:10000]}"
                summary = await _call_or("nvidia/nemotron-3-ultra-550b-a55b:free", sum_prompt)
                if not summary or any(p in summary.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai"]):
                    logger.warning(f"Nemotron failed summarization, falling back to {OR_FALLBACK_MODEL}...")
                    fallback = await _call_or(OR_FALLBACK_MODEL, sum_prompt)
                    if fallback and not any(p in fallback.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai"]):
                        summary = fallback
                    else:
                        logger.warning("Fallback failed summarization, falling back to local G1 Flash...")
                        from ai_processor import call_agy
                        summary = call_agy(sum_prompt, timeout=120, model="flash")
                if not summary: summary = "Summary unavailable."
                
                combined_research += f"\n### Source: {url}\n{summary}\n"
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                
        # 4. Save to study database
        db_dir = os.path.join(base_dir, "study_database")
        os.makedirs(db_dir, exist_ok=True)
        filename = f"{topic.replace(' ', '_').lower()}.md"
        with open(os.path.join(db_dir, filename), "w") as f:
            f.write(f"# Pre-Cached Research: {topic}\n{combined_research}")
            
        logger.info(f"Successfully cached research for {topic}")
        
    except Exception as e:
        logger.error(f"Web pre-cacher failed: {e}")

if __name__ == "__main__":
    asyncio.run(pre_cache_web())

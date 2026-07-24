import os
import json
import logging
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
       
        def _read_brain():
            with open(brain_file, "r") as f:
                return f.read()
        brain = await asyncio.to_thread(_read_brain)
       
        # 1. Ask local model what topics we should research
        logger.info("Asking local model to identify research topics...")
        prompt = (
            "Based on the following curated brain of a student, identify ONE specific academic topic they are currently learning that would benefit from extra web research (e.g., 'Quadratic Formula', 'Cellular Respiration').\n"
            "Reply with ONLY the topic name. If there are no academic topics, reply with 'NONE'.\n\n"
            f"BRAIN:\n{brain}"
        )
        
        from llm_router import call_local_rpc
        
        # Try local RPC first (PRIVATE data)
        topic = await asyncio.to_thread(
            call_local_rpc, 
            prompt=prompt, 
            max_tokens=50, 
            timeout=120, 
            classification="PRIVATE"
        )
        
        if not topic or any(p in topic.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai", "none", "⚠️"]):
            logger.info("No valid topics found or local inference failed.")
            return

        if not topic: topic = ""
        topic = re.sub(r'[^a-zA-Z0-9\s]', '', topic)
       
        if not topic or "NONE" in topic.upper() or len(topic) > 50:
            logger.info("No valid topics found to research.")
            return
           
        logger.info(f"Identified topic for pre-caching: {topic}")
       
        # 2. Search the web (using a simple DuckDuckGo HTML scrape)
        from urllib.parse import quote_plus
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(topic + ' explanation examples')}"
       
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)) as client:
            res = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})

        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all('a', class_='result__snippet', limit=3)
        urls_to_scrape = [a['href'] for a in results if 'href' in a.attrs]

        # DuckDuckGo returns URLs in several forms that httpx 0.28+ rejects:
        #   - protocol-relative: //duckduckgo.com/l/?uddg=... -> prepend "https:"
        #   - path-relative:     /l/?uddg=...                   -> prepend "https://duckduckgo.com"
        # Normalize both so the scraping client (with follow_redirects=True)
        # follows the uddg redirect chain to the actual target.
        def _normalize(u):
            if u.startswith("//"):
                return "https:" + u
            if u.startswith("/"):
                return "https://duckduckgo.com" + u
            return u
        urls_to_scrape = [_normalize(u) for u in urls_to_scrape]

        if not urls_to_scrape:
            logger.warning("No search results found.")
            return

        # 3. Scrape the sites and summarize
        combined_research = ""
        for url in urls_to_scrape:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)) as client:
                    page_res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                page_soup = BeautifulSoup(page_res.text, "html.parser")
                text = " ".join([p.text for p in page_soup.find_all('p')])
               
                # Summarize — PUBLIC classification since it's web text
                sum_prompt = f"Summarize the following educational text about {topic}. Extract key formulas, facts, and examples.\n\nTEXT:\n{text[:10000]}"
                summary = await asyncio.to_thread(
                    call_local_rpc, 
                    prompt=sum_prompt, 
                    max_tokens=500, 
                    timeout=120, 
                    classification="PUBLIC"
                )
                if not summary or any(p in summary.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai", "⚠️"]):
                    summary = "Summary unavailable."
               
                combined_research += f"\n### Source: {url}\n{summary}\n"
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
               
        # 4. Save to study database
        db_dir = os.path.join(base_dir, "study_database")
        
        def _save_research():
            os.makedirs(db_dir, exist_ok=True)
            filename = f"{topic.replace(' ', '_').lower()}.md"
            with open(os.path.join(db_dir, filename), "w") as f:
                f.write(f"# Pre-Cached Research: {topic}\n{combined_research}")
                
        await asyncio.to_thread(_save_research)

           
        logger.info(f"Successfully cached research for {topic}")
       
    pass

if __name__ == "__main__":
    asyncio.run(pre_cache_web())

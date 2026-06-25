import os
import glob
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = "/home/sanel/personal-assistant-bot"
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
AGENTAPI_BIN = "/home/sanel/.local/bin/agy"

def run_overnight_research():
    os.makedirs(KB_DIR, exist_ok=True)
    
    brain_file = os.path.join(BASE_DIR, "curated_brain.md")
    summaries = os.path.join(BASE_DIR, "scrapers", "source_cache", "combined_summaries.txt")
    
    context = ""
    if os.path.exists(brain_file):
        with open(brain_file, "r") as f:
            context += f.read() + "\n"
    if os.path.exists(summaries):
        with open(summaries, "r") as f:
            context += f.read()[:10000] # first 10k chars
            
    if not context.strip():
        logger.warning("No context found to extract topics from.")
        return

    logger.info("Extracting pure academic/general topics from context using local model (PII safe)...")
    topic_prompt = (
        "You are an academic topic extractor. Read the following personal context and extract ONLY the academic, general, or professional topics "
        "that require deep-dive research (e.g. 'Quadratic Equations', 'American Revolution', 'Photosynthesis', 'SAT Math').\n"
        "DO NOT include any names, personal info, dates, or specific assignment names (like 'Day 9 Homework'). "
        "Just output a comma-separated list of 3-5 core academic topics found in the text. Nothing else.\n\n"
        f"CONTEXT:\n{context}"
    )
    
    try:
        r = subprocess.run([AGENTAPI_BIN, "--model", "flash", "--dangerously-skip-permissions", "--print", topic_prompt], 
                           capture_output=True, text=True, timeout=120)
        topics_raw = r.stdout.strip()
        
        # Clean up output
        if "```" in topics_raw:
            topics_raw = topics_raw.split("```")[1].lstrip("json").lstrip()
            
        topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
    except Exception as e:
        logger.error(f"Failed to extract topics: {e}")
        return
        
    logger.info(f"Extracted topics to research: {topics}")
    
    for topic in topics[:5]: # Max 5 topics a night
        safe_topic = "".join(c for c in topic if c.isalnum() or c in " -_").strip()
        kb_file = os.path.join(KB_DIR, f"{safe_topic.replace(' ', '_').lower()}.md")
        
        if os.path.exists(kb_file):
            logger.info(f"Skipping {topic}, already researched.")
            continue
            
        logger.info(f"Researching topic: {topic} using the upgraded Mega Study Builder...")
        
        try:
            # We now route the knowledge base directly through the 100-page Visual Image Pipeline
            import sys
            sys.path.insert(0, BASE_DIR)
            from scrapers.mega_study_builder import generate_mega_guide
            
            research_text = generate_mega_guide(topic)
            
            if research_text and len(research_text) > 1000:
                with open(kb_file, "w") as f:
                    f.write(research_text)
                logger.info(f"Saved massive research guide for {topic} ({len(research_text)} bytes).")
            else:
                logger.warning(f"Research for {topic} completely failed or was too short.")
        except Exception as e:
            logger.error(f"Failed to build guide for {topic}: {e}")

if __name__ == "__main__":
    run_overnight_research()

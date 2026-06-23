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
            topics_raw = topics_raw.split("```")[1]
            
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
            
        logger.info(f"Researching topic: {topic} using free online model...")
        
        # Inject knowledge gaps if they exist
        gaps_text = ""
        gaps_dir = os.path.join(BASE_DIR, "knowledge_gaps")
        if os.path.exists(gaps_dir):
            for gap_file in glob.glob(os.path.join(gaps_dir, "*.txt")):
                with open(gap_file, "r") as gf:
                    gaps_text += f"\n- " + gf.read().strip()
        
        gaps_instruction = ""
        if gaps_text.strip():
            gaps_instruction = f"\n\nCRITICAL KNOWLEDGE GAPS:\nThe student has recently struggled with the following concepts. You MUST heavily emphasize these weaknesses in your study guide and include highly targeted practice questions to fix them:\n{gaps_text}"
        
        research_prompt = (
            f"Write a comprehensive, highly-detailed study guide and knowledge base article about: {topic}. "
            "Include definitions, formulas, historical context, advanced concepts, and common pitfalls. "
            "Format it beautifully in Markdown. This will be cached in a student's offline database."
            f"{gaps_instruction}"
        )
        
        try:
            logger.info("Attempting research with Nemotron...")
            rr = subprocess.run([AGENTAPI_BIN, "--model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free", 
                                 "--dangerously-skip-permissions", "--print", research_prompt], 
                                capture_output=True, text=True, timeout=300)
            research_text = rr.stdout.strip()
            
            if len(research_text) < 100 or "⚠️" in research_text:
                raise Exception("Nemotron returned short or error response.")
        except Exception as e:
            logger.warning(f"Nemotron failed ({e}). Falling back to Owl Alpha...")
            try:
                rr2 = subprocess.run([AGENTAPI_BIN, "--model", "openrouter:openrouter/owl-alpha", 
                                     "--dangerously-skip-permissions", "--print", research_prompt], 
                                    capture_output=True, text=True, timeout=300)
                research_text = rr2.stdout.strip()
            except Exception as e2:
                logger.error(f"Owl Alpha also failed: {e2}")
                research_text = ""
            
        if len(research_text) > 100 and "⚠️" not in research_text:
            with open(kb_file, "w") as f:
                f.write(research_text)
            logger.info(f"Saved research for {topic} ({len(research_text)} bytes).")
        else:
            logger.warning(f"Research for {topic} completely failed or was too short.")

if __name__ == "__main__":
    run_overnight_research()

import os
import glob
import subprocess
import logging
from config import COMBINED_SUMMARIES_FILE, CURATED_BRAIN_FILE
try:
    import telegram_logger
    telegram_logger.setup_telegram_logging()
except Exception:
    pass


logger = logging.getLogger(__name__)

BASE_DIR = "/home/sanel/personal-assistant-bot"
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")


def _agy_model(alias: str) -> str:
    """Resolve an internal agy alias (flash/pro) to the current valid model ID."""
    try:
        import sys
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        from llm_router import _resolve_agy_model
        return _resolve_agy_model(alias)
    except Exception:
        return "Gemini 3.1 Pro (Low)" if alias == "pro" else "Gemini 3.5 Flash (Medium)"
AGENTAPI_BIN = "/home/sanel/.local/bin/agy"

def run_overnight_research():
    """
    Run overnight research pipeline with RPC-aware fallbacks.

    Order of preference:
      1. RPC llama-server (7B+ model) — for deep, high-quality research
      2. agy flash (local) — fast but less thorough
      3. Mega Study Builder (cloud via OpenRouter) — full power, uses credits

    Each stage checks availability and falls back gracefully.
    """
    os.makedirs(KB_DIR, exist_ok=True)
    
    brain_file = CURATED_BRAIN_FILE
    summaries = COMBINED_SUMMARIES_FILE
    
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

    # ── Step 1: Extract topics (lightweight — always use agy flash) ──────
    logger.info("Extracting academic topics from context using agy flash (PII safe)...")
    topic_prompt = (
        "You are an academic topic extractor. Read the following personal context and extract ONLY the academic, general, or professional topics "
        "that require deep-dive research (e.g. 'Quadratic Equations', 'American Revolution', 'Photosynthesis', 'SAT Math').\n"
        "DO NOT include any names, personal info, dates, or specific assignment names (like 'Day 9 Homework'). "
        "Just output a comma-separated list of 3-5 core academic topics found in the text. Nothing else.\n\n"
        f"CONTEXT:\n{context}"
    )
    
    try:
        r = subprocess.run([AGENTAPI_BIN, "--model", _agy_model("flash"), "--dangerously-skip-permissions", "--print", topic_prompt],
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

    # ── Step 2: Research each topic (RPC first, with fallbacks) ──────────
    for topic in topics[:5]:  # Max 5 topics a night
        safe_topic = "".join(c for c in topic if c.isalnum() or c in " -_").strip()
        kb_file = os.path.join(KB_DIR, f"{safe_topic.replace(' ', '_').lower()}.md")
        
        if os.path.exists(kb_file):
            logger.info(f"Skipping {topic}, already researched.")
            continue
            
        logger.info(f"Researching topic: {topic}")
        
        research_text = _research_topic_with_fallbacks(topic, context)
        
        if research_text and len(research_text) > 500:
            with open(kb_file, "w") as f:
                f.write(research_text)
            logger.info(f"Saved research guide for {topic} ({len(research_text)} chars).")
        else:
            logger.warning(f"Research for {topic} failed or was too short — all fallbacks exhausted.")


def _research_topic_with_fallbacks(topic: str, context: str) -> str:
    """
    Research a single topic with fallback chain:
      1. RPC llama-server (7B+, highest quality)
      2. Mega Study Builder (cloud, full power)
      3. agy flash (local, lightweight)
    """
    research_prompt = (
        f"Create a comprehensive study guide for: {topic}\n\n"
        f"Include:\n"
        f"- Key concepts and definitions\n"
        f"- Important formulas, principles, or dates\n"
        f"- Step-by-step problem-solving approaches\n"
        f"- Common mistakes and how to avoid them\n"
        f"- Practice problem types with solutions\n\n"
        f"Context from user's notes:\n{context[:5000]}\n\n"
        f"Be thorough and detailed — this runs overnight."
    )

    # ── Try 1: RPC llama-server (best quality for academic content) ───
    try:
        from llm_router import call_llamacpp_rpc_with_fallback, is_rpc_server_healthy
        if is_rpc_server_healthy():
            logger.info(f"  Attempting RPC for '{topic}'...")
            result = call_llamacpp_rpc_with_fallback(
                prompt=research_prompt,
                system_prompt="You are an expert academic tutor creating comprehensive study materials.",
                max_tokens=4000,
                task=f"overnight-research-{topic[:30]}",
                timeout=600,
                skip_cloud_fallback=True,
            )
            if result and len(result) > 500:
                logger.info(f"  RPC success for '{topic}' ({len(result)} chars)")
                return result
            logger.warning(f"  RPC returned insufficient content for '{topic}', trying next fallback")
        else:
            logger.info(f"  RPC server not healthy, skipping RPC for '{topic}'")
    except ImportError:
        logger.info(f"  llm_router not available, skipping RPC for '{topic}'")
    except Exception as e:
        logger.warning(f"  RPC failed for '{topic}': {e}")

    # ── Try 2: Mega Study Builder (cloud, best quality) ──────────────
    try:
        import sys
        sys.path.insert(0, BASE_DIR)
        from scrapers.mega_study_builder import generate_mega_guide
        logger.info(f"  Attempting Mega Study Builder for '{topic}'...")
        result = generate_mega_guide(topic)
        if result and len(result) > 500:
            logger.info(f"  Mega Study Builder success for '{topic}' ({len(result)} chars)")
            return result
        logger.warning(f"  Mega Study Builder returned insufficient content for '{topic}'")
    except Exception as e:
        logger.warning(f"  Mega Study Builder failed for '{topic}': {e}")

    # ── Try 3: agy flash (local, last resort) ────────────────────────
    try:
        logger.info(f"  Falling back to agy flash for '{topic}'...")
        r = subprocess.run(
            [AGENTAPI_BIN, "--model", _agy_model("flash"), "--dangerously-skip-permissions", "--print", research_prompt],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0 and r.stdout.strip():
            result = r.stdout.strip()
            logger.info(f"  agy flash success for '{topic}' ({len(result)} chars)")
            return result
    except Exception as e:
        logger.error(f"  agy flash failed for '{topic}': {e}")

    return ""

if __name__ == "__main__":
    run_overnight_research()

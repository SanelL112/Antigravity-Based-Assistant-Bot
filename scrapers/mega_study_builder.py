import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from youtubesearchpython import VideosSearch
from youtube_transcript_api import YouTubeTranscriptApi
from ai_processor import call_agy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MEGA_STUDY_PROMPT = """You are an elite academic tutor. I am trying to build a master study guide for the topic: "{topic}".
I have autonomously pulled in context from multiple sources, including the teacher's handwritten notes. Synthesize all of this information into the ultimate, extremely comprehensive, beautifully formatted Markdown study guide.

--- TEACHER'S HANDWRITTEN NOTES ---
{pdf_text}

--- YOUTUBE TRANSCRIPT ({yt_title}) ---
{transcript}

--- WEB ARTICLE SUMMARY ({web_title}) ---
{web_text}

--- YOUR INSTRUCTIONS ---
Using the provided context and your own vast knowledge, you MUST be as exhaustive and detailed as possible. Do not skip over nuances.
1. **In-Depth Summary**: Create an incredibly detailed, exhaustive explanation of the topic.
2. **Core Concepts & Formulas**: Break down every single key formula, date, vocabulary word, or core concept (especially prioritizing the teacher's notes).
3. **Step-by-Step Tutorial**: Create a comprehensive timeline or step-by-step tutorial explaining how to solve problems or understand the workflow.
4. **Action Plan (What I Need To Do)**: Tell me exactly what I need to do next to master this topic. Give me a clear checklist of specific concepts to memorize, tasks to complete, and areas to focus on.
5. **Practice Exam**: Write 5 highly challenging practice questions with a detailed answer key at the very bottom.
6. **Topic Contextualization**: Even if the provided notes or PDFs do not explicitly mention "{topic}" by name, you MUST extract their underlying concepts and apply them directly to "{topic}". (For example, if the topic is the SAT, aggressively frame the grammar and math concepts from the notes specifically around how they are tested on the SAT).

CRITICAL FORMATTING RULES: 
- Your final output MUST be a pristine, highly structured, professional study guide.
- ABSOLUTELY NO INTERNAL MONOLOGUES or "thinking out loud" (e.g. "Wait, let me re-evaluate...", "Let's assume the problem was..."). 
- You MUST wrap ALL of your internal planning, calculations, or problem-solving scratchpad inside <thought>...</thought> tags! Anything outside these tags must be the final, polished study guide text.
"""

def search_web_article(topic: str):
    try:
        results = DDGS().text(f"{topic} tutorial explanation", max_results=2)
        if not results:
            return None, ""
        url = results[0]["href"]
        title = results[0]["title"]
        
        # Try to scrape it
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        text = " ".join([p.text for p in soup.find_all("p")])
        return {"title": title, "link": url}, text[:10000] # Cap at 10k chars
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return None, ""

def search_youtube(topic: str):
    try:
        videosSearch = VideosSearch(f"{topic} educational tutorial", limit=1)
        result = videosSearch.result()
        if result and "result" in result and len(result["result"]) > 0:
            video = result["result"][0]
            transcript_list = YouTubeTranscriptApi.get_transcript(video["id"])
            text = " ".join([item["text"] for item in transcript_list])
            return {"title": video["title"], "link": video["link"]}, text[:15000]
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        return None, ""

def generate_mega_guide(topic: str, pdf_text: str = "") -> str:
    """Generates the ultimate study guide."""
    logger.info(f"Generating MEGA guide for: {topic}")
    
    yt_meta, yt_text = search_youtube(topic)
    web_meta, web_text = search_web_article(topic)
    
    pdf_exports_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "pdf_exports.txt")
    has_cache = os.path.exists(pdf_exports_file)
    if not yt_meta and not web_meta and not pdf_text and not has_cache:
        return f"❌ I couldn't find any good web or YouTube sources for '{topic}'."
        
    # Pull in the user's internal notes from Canvas/Docs/Classroom and Extracted PDFs
    internal_notes = ""
    notes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "combined_summaries.txt")
    pdf_exports_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "pdf_exports.txt")
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, "r") as f:
                internal_notes += f.read().strip()
        except Exception:
            pass
            
    if os.path.exists(pdf_exports_file):
        try:
            with open(pdf_exports_file, "r") as f:
                internal_notes += "\n\n" + f.read().strip()
        except Exception:
            pass
            
    delta_export_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "offline_archive", "delta_export.txt")
    if os.path.exists(delta_export_file):
        try:
            with open(delta_export_file, "r") as f:
                internal_notes += "\n\n" + f.read().strip()
        except Exception:
            pass
            
    if not internal_notes:
        internal_notes = "None"

    prompt = MEGA_STUDY_PROMPT.format(
        topic=topic,
        pdf_text=pdf_text if pdf_text else "No handwritten notes provided.",
        yt_title=yt_meta["title"] if yt_meta else "No Video",
        transcript=yt_text if yt_text else "None",
        web_title=web_meta["title"] if web_meta else "No Web Article",
        web_text=web_text if web_text else "None"
    )
    
    # Append the internal notes to the prompt dynamically
    prompt += f"\n\n--- YOUR PERSONAL NOTES (CANVAS/CLASSROOM/DOCS) ---\n{internal_notes}\n"
    
    logger.info("Sending mega prompt to OpenRouter Nemotron...")
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ Missing OPENROUTER_API_KEY in .env"
        
    def _call_or():
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/SanelL112/TaskBot",
                    "X-Title": "TaskBot"
                },
                json={
                    "models": ["openrouter/owl-alpha"],
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=180.0
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            return None
        except Exception:
            return None
            
    guide_content = _call_or()
    
    if not guide_content or any(p in guide_content.lower()[:50] for p in ["i cannot", "i'm sorry", "i don't know", "as an ai"]):
        logger.warning("OpenRouter failed or refused to build study guide. Offloading to local G1 Flash...")
        from ai_processor import call_agy
        fallback_g1 = call_agy(prompt, timeout=180, model="flash")
        if fallback_g1:
            guide_content = fallback_g1
                
    if guide_content:
        import re
        guide_content = re.sub(r'<thought>.*?</thought>', '', guide_content, flags=re.DOTALL).strip()
        guide_content += "\n\n*(Generated by the Auto-Fallback Engine)*"
        
    final_message = f"🧠 **ULTIMATE STUDY GUIDE: {topic}**\n\n{guide_content}\n\n**Sources Used:**\n"
    if yt_meta:
        final_message += f"- 📺 [{yt_meta['title']}]({yt_meta['link']})\n"
    if web_meta:
        final_message += f"- 🌐 [{web_meta['title']}]({web_meta['link']})\n"
        
    return final_message

def build_guide_for_drive_file(file_id: str, topic: str):
    import tempfile
    from google_scraper import download_drive_file
    from extract_notes import transcribe_handwritten_pdf
    
    logger.info(f"Building guide for Drive file {file_id} on topic {topic}")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    
    success = download_drive_file(file_id, path)
    if not success:
        return "❌ Failed to download the PDF from Google Drive. Ensure I have access."
        
    transcript = transcribe_handwritten_pdf(path)
    os.remove(path)
    
    if "Error:" in transcript:
        return f"❌ {transcript}"
        
    return generate_mega_guide(topic, pdf_text=transcript)

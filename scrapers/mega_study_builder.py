import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from youtubesearchpython import VideosSearch
from youtube_transcript_api import YouTubeTranscriptApi
from ai_processor import call_agy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MEGA_STUDY_PROMPT = """You are an elite academic tutor. I am trying to build a master study guide for the topic: "{topic}".
I have autonomously pulled in context from multiple sources, including the teacher's handwritten notes, web articles, and YouTube transcripts. Synthesize all of this information into the ultimate, extremely comprehensive, beautifully formatted Markdown study guide.

--- TEACHER'S HANDWRITTEN NOTES ---
{pdf_text}

--- YOUTUBE TRANSCRIPTS ({yt_title}) ---
{transcript}

--- WEB ARTICLE SUMMARIES ({web_title}) ---
{web_text}

--- YOUR INSTRUCTIONS ---
Using the provided context and your own vast knowledge, you MUST be as exhaustive and detailed as possible. Do not skip over nuances.
YOUR OUTPUT MUST BE EXTREMELY LONG. THERE IS NO MAXIMUM LIMIT. The guide can be 50+ pages if necessary. Do not restrict yourself. Expand endlessly on every single point, breaking them down into microscopic details.
HOWEVER, because you have an output token limit, you MUST spend 90% of your response deeply expanding on Formulas, Theorems, and Explanations. Do NOT waste all your output tokens on practice problems!

You MUST follow this exact strict format:
1. **Core Formulas & Theorems (MASSIVE EXPANSION)**: Break down every single key formula, date, vocabulary word, or core concept. Prioritize the teacher's classroom notes. Expand on this section endlessly.
2. **Deep-Dive Explanations**: Provide incredibly detailed, exhaustive explanations of the topic. Explain the "Why" and the "How".
3. **Advanced Strategies & Tactics**: Create a comprehensive list of strategies, workflow timelines, and exact step-by-step tactics to master the topic.
4. **Action Plan (What I Need To Do)**: Tell me exactly what I need to do next to master this topic. Give me a clear checklist of specific concepts to memorize.
5. **Practice Exam**: Write 5 highly challenging practice problems with a detailed step-by-step answer key at the very bottom.
6. **Topic Contextualization**: Even if the provided notes or PDFs do not explicitly mention "{topic}" by name, you MUST extract their underlying concepts and apply them directly to "{topic}".

CRITICAL FORMATTING RULES: 
- Your final output MUST be a pristine, highly structured, professional study guide.
- ABSOLUTELY NO INTERNAL MONOLOGUES or "thinking out loud".
- You MUST wrap ALL of your internal planning or calculations inside <thought>...</thought> tags! Anything outside these tags must be the final, polished study guide text.
"""

def search_web_article(topic: str):
    try:
        queries = [f"{topic} tutorial", f"{topic} explanation", f"{topic} study guide", f"{topic} practice problems", f"{topic} advanced concepts"]
        combined_text = ""
        meta_titles = []
        
        for q in queries:
            try:
                results = DDGS().text(q, max_results=20)
                if not results: continue
                
                for res in results:
                    if len(meta_titles) >= 100: break
                    if res["title"] in meta_titles: continue
                    
                    try:
                        resp = requests.get(res["href"], timeout=5)
                        soup = BeautifulSoup(resp.content, "html.parser")
                        combined_text += f"\n--- SOURCE: {res['title']} ---\n"
                        combined_text += " ".join([p.text for p in soup.find_all("p")])
                        meta_titles.append(res["title"])
                    except Exception:
                        continue
            except Exception:
                pass
            if len(meta_titles) >= 100: break
                
        if meta_titles:
            return {"title": f"Fetched {len(meta_titles)} Web Articles | " + " | ".join(meta_titles[:5]) + "...", "link": "Multiple Sources"}, combined_text
        return None, ""
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return None, ""

def search_youtube(topic: str):
    try:
        videosSearch = VideosSearch(f"{topic} educational tutorial", limit=20)
        combined_text = ""
        meta_titles = []
        
        for _ in range(5): # Loop 5 pages (5 * 20 = 100 videos)
            try:
                result = videosSearch.result()
                if not result or "result" not in result or not result["result"]: break
                
                for video in result["result"]:
                    if len(meta_titles) >= 100: break
                    try:
                        transcript_list = YouTubeTranscriptApi.get_transcript(video["id"])
                        combined_text += f"\n--- VIDEO: {video['title']} ---\n"
                        combined_text += " ".join([item["text"] for item in transcript_list])
                        meta_titles.append(video["title"])
                    except Exception:
                        continue
                videosSearch.next()
            except Exception:
                break
                
        if meta_titles:
            return {"title": f"Fetched {len(meta_titles)} YouTube Transcripts | " + " | ".join(meta_titles[:5]) + "...", "link": "Multiple Videos"}, combined_text
        return None, ""
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        return None, ""

def generate_mega_guide(topic: str, pdf_text: str = "") -> str:
    """Generates the ultimate chunked study guide."""
    logger.info(f"Generating MEGA guide for: {topic} using Chunking Architecture")
    
    # Strip out generic filler words so the scrapers search for the actual subject matter
    search_topic = topic.lower()
    for filler in ["comprehensive", "study guide", "prep guide", "ultimate", "master class", "crash course", "review"]:
        search_topic = search_topic.replace(filler, "")
    search_topic = search_topic.strip()
    if not search_topic:
        search_topic = topic # Fallback just in case
    
    yt_meta, yt_text = search_youtube(search_topic)
    web_meta, web_text = search_web_article(search_topic)
    
    # Pull in the user's internal notes from Canvas/Docs/Classroom and Extracted PDFs
    internal_notes = ""
    notes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "combined_summaries.txt")
    pdf_exports_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_cache", "pdf_exports.txt")
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, "r") as f:
                internal_notes += f.read().replace('\x00', '').strip()
        except Exception:
            pass
            
    if os.path.exists(pdf_exports_file):
        try:
            with open(pdf_exports_file, "r") as f:
                internal_notes += "\n\n" + f.read().replace('\x00', '').strip()
        except Exception:
            pass
            
    delta_export_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "offline_archive", "delta_export.txt")
    if os.path.exists(delta_export_file):
        try:
            with open(delta_export_file, "r") as f:
                internal_notes += "\n\n" + f.read().replace('\x00', '').strip()
        except Exception:
            pass
            
    if not internal_notes:
        internal_notes = "None"

    source_context = f"""
--- TEACHER'S HANDWRITTEN NOTES & CLASSROOM PDFS ---
{pdf_text if pdf_text else "None"}

--- YOUR PERSONAL NOTES (CANVAS/CLASSROOM/DOCS) ---
{internal_notes}

--- YOUTUBE TRANSCRIPTS ({yt_meta["title"] if yt_meta else "None"}) ---
{yt_text if yt_text else "None"}

--- WEB ARTICLE SUMMARIES ({web_meta["title"] if web_meta else "None"}) ---
{web_text if web_text else "None"}
"""

    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ Missing OPENROUTER_API_KEY in .env"
        
    def _call_or(prompt_text):
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
                    "messages": [{"role": "user", "content": prompt_text}]
                },
                timeout=300.0
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            return None
        except Exception as e:
            logger.error(f"OpenRouter chunk failure: {e}")
            return None

    # PHASE 1: Generate Master Outline
    logger.info("PHASE 1: Generating Master Outline...")
    outline_prompt = f"""You are an elite academic tutor planning a 50+ page massive study guide for "{topic}".
Here are the sources you have available:
{source_context}

Create a highly detailed 10-chapter outline for this study guide. 
Ensure you include chapters for Core Formulas, Deep-Dive Explanations, Advanced Strategies, and Practice Problems.
Respond ONLY with a raw JSON array of strings representing the chapter titles. Do not include markdown blocks or any other text.
Example: ["Chapter 1: Introduction to Formulas", "Chapter 2: Advanced Mechanics"]"""
    
    outline_json_str = _call_or(outline_prompt)
    import json
    outline = []
    if outline_json_str:
        try:
            # Try to strip markdown JSON blocks if the AI disobeyed
            clean_json = outline_json_str.replace("```json", "").replace("```", "").strip()
            outline = json.loads(clean_json)
        except Exception as e:
            logger.error(f"Failed to parse outline JSON: {e}")
            
    if not outline or not isinstance(outline, list):
        logger.warning("Falling back to default outline.")
        outline = [
            "Chapter 1: Core Concepts & Vocabulary",
            "Chapter 2: Essential Formulas & Theorems",
            "Chapter 3: Deep-Dive Explanations Part 1",
            "Chapter 4: Deep-Dive Explanations Part 2",
            "Chapter 5: Advanced Strategies & Tactics",
            "Chapter 6: Step-by-Step Problem Solving Frameworks",
            "Chapter 7: Real-World Applications",
            "Chapter 8: Action Plan & Memorization Checklist",
            "Chapter 9: Common Mistakes & Pitfalls",
            "Chapter 10: Master Practice Exam (5 Hard Problems with Solutions)"
        ]

    # PHASE 2: Chunked Generation
    logger.info(f"PHASE 2: Generating {len(outline)} Chapters...")
    full_guide_content = ""
    
    for i, chapter in enumerate(outline):
        logger.info(f"Generating Chunk {i+1}/{len(outline)}: {chapter}")
        chunk_prompt = f"""You are an elite academic tutor writing a 50+ page massive study guide for "{topic}".
Here are the sources you have available:
{source_context}

Your current task is to write ONLY the content for: **{chapter}**

INSTRUCTIONS:
1. Expand on this chapter endlessly. Do not hold back. Break down every microscopic detail, nuance, and explanation.
2. Assume the reader needs an incredibly rigorous, textbook-level deep dive.
3. If this chapter is about Formulas, explain how they are derived and when to use them. If it is about Practice Problems, write highly challenging ones with step-by-step answers.
4. ABSOLUTELY NO INTERNAL MONOLOGUES or "thinking out loud".
5. Wrap ALL of your internal planning or calculations inside <thought>...</thought> tags! Anything outside these tags must be the final, polished text for the chapter.
6. Start your output directly with a Markdown Header for the chapter (e.g. # {chapter}).
"""
        chunk_result = _call_or(chunk_prompt)
        
        if not chunk_result:
            logger.warning(f"Failed to generate chunk {chapter}, trying local fallback...")
            from ai_processor import call_agy
            chunk_result = call_agy(chunk_prompt, timeout=180, model="flash")
            
        if chunk_result:
            import re
            chunk_result = re.sub(r'<thought>.*?</thought>', '', chunk_result, flags=re.DOTALL).strip()
            full_guide_content += f"\n\n{chunk_result}\n\n---\n"
        else:
            full_guide_content += f"\n\n# {chapter}\n\n*(Failed to generate this section)*\n\n---\n"

    # PHASE 3: Assembly
    final_message = f"🧠 **ULTIMATE CHUNKED STUDY GUIDE: {topic}**\n\n*(Generated dynamically via a {len(outline)}-part LLM Chunking Pipeline to bypass token limits)*\n\n{full_guide_content}\n\n**Sources Used:**\n- Classroom PDFs (Local Brain Sync)"
    if yt_meta:
        final_message += f"\n- YouTube: {yt_meta['title']}"
    if web_meta:
        final_message += f"\n- Web: {web_meta['title']}"
        
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

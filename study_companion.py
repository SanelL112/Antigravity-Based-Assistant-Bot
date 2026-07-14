import os
import sys
import json
import logging
try:
    import telegram_logger
    telegram_logger.setup_telegram_logging()
except Exception:
    pass

from youtubesearchpython import VideosSearch
from youtube_transcript_api import YouTubeTranscriptApi

# Ensure project root is on sys.path for standalone usage
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from ai_processor import call_agy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STUDY_GUIDE_PROMPT = """You are an expert tutor. I am trying to study the topic: "{topic}".
I found a highly-rated YouTube video about this, and here is the raw transcript from the video:

{transcript}

Based ONLY on this transcript and your general knowledge of the topic, please create a comprehensive, beautifully formatted study guide for me in Markdown.
Include:
1. A brief overview of the topic.
2. The key concepts and definitions extracted from the video.
3. Step-by-step breakdowns or formulas if applicable.
4. 3-5 practice questions I can use to test my knowledge.

Be concise but extremely informative.
"""

def search_youtube(topic: str) -> dict:
    """Searches YouTube and returns the top video info."""
    try:
        videosSearch = VideosSearch(f"{topic} educational tutorial", limit=1)
        result = videosSearch.result()
        if result and "result" in result and len(result["result"]) > 0:
            video = result["result"][0]
            return {
                "id": video.get("id"),
                "title": video.get("title"),
                "link": video.get("link"),
                "channel": video.get("channel", {}).get("name", "Unknown")
            }
    except TypeError as e:
        if "proxies" in str(e):
            # youtubesearchpython version mismatch - try without proxies
            logger.warning("YouTube search: proxies parameter issue, retrying with basic search")
            try:
                videosSearch = VideosSearch(f"{topic} educational tutorial", limit=1)
                result = videosSearch.result()
                if result and "result" in result and len(result["result"]) > 0:
                    video = result["result"][0]
                    return {
                        "id": video.get("id"),
                        "title": video.get("title"),
                        "link": video.get("link"),
                        "channel": video.get("channel", {}).get("name", "Unknown")
                    }
            except Exception as e2:
                logger.error(f"YouTube search error (retry): {e2}")
        else:
            logger.error(f"YouTube search error: {e}")
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
    return None

def get_transcript(video_id: str) -> str:
    """Fetches the transcript for a video ID."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([item["text"] for item in transcript_list])
        return text
    except Exception as e:
        logger.error(f"Transcript error for {video_id}: {e}")
        return None

def generate_study_guide(topic: str) -> str:
    """Generates a study guide for a topic using YouTube transcripts and AI."""
    logger.info(f"Generating study guide for: {topic}")
    
    video = search_youtube(topic)
    if not video:
        return f"❌ I couldn't find any good YouTube videos for the topic: '{topic}'."
        
    logger.info(f"Found video: {video['title']} ({video['link']})")
    
    transcript = get_transcript(video["id"])
    if not transcript:
        return f"❌ I found a great video ('{video['title']}'), but it doesn't have closed captions available, so I can't read it!"
        
    # Trim transcript to ~15000 chars to avoid overwhelming the model
    # agy Pro can handle huge contexts, but 15k is safe and fast
    transcript = transcript[:15000]
    
    prompt = STUDY_GUIDE_PROMPT.format(topic=topic, transcript=transcript)
    
    logger.info("Sending transcript to agy Pro for study guide generation...")
    guide_content = call_agy(prompt, timeout=120)
    
    if not guide_content:
        return "❌ The AI failed to generate a study guide. Please try again later."
        
    final_message = (
        f"🎓 **Study Guide Generated!**\n\n"
        f"📺 **Source Video:** [{video['title']}]({video['link']}) by {video['channel']}\n\n"
        f"{guide_content}"
    )
    
    return final_message

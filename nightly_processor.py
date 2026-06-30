import asyncio
import os
import sys
import datetime
import subprocess

# Ensure the parent directory is in sys.path
sys.path.append("/home/sanel/personal-assistant-bot")

from scrapers.mega_study_builder import generate_mega_guide
import requests

def extract_dynamic_topics(pdf_text: str, num_topics: int = 3) -> list:
    """Uses the AI to extract new, highly specific topics from the user's classroom notes."""
    prompt = f"""You are an intelligent topic extractor. Scan the following classroom notes and identify exactly {num_topics} distinct, highly specific academic topics or chapters that would make great study guides.
Respond ONLY with a comma-separated list of the topics. Do not include bullet points or numbers.
Example: Quadratic Equations, Civil War History, Biology Cell Structure

Notes:
{pdf_text[:15000]}
"""
    print("Extracting dynamic topics from classroom notes using OpenRouter...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv("/home/sanel/personal-assistant-bot/.env")
        api_key = os.getenv("OPENROUTER_API_KEY")
        
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "models": ["meta-llama/llama-3.3-70b-instruct:free", "nvidia/nemotron-3-ultra-550b-a55b:free"],
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=600
        )
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            topics = [t.strip() for t in result.split(",") if t.strip()]
            return topics[:num_topics]
    except Exception as e:
        print(f"Extraction error: {e}")
        
    return ["General Mathematics", "Advanced Grammar", "Test Strategies"]

def build_and_push(topic: str):
    """Generates or updates the massive study guide and automatically pushes it to GitHub."""
    print(f"\n==============================================")
    print(f"Starting Nightly Build Pipeline for: {topic}")
    print(f"==============================================\n")
    
    filename_base = topic.replace(" ", "_").replace("/", "_")
    output_md = f"/home/sanel/personal-assistant-bot/study_guides/{filename_base}_Study_Guide.md"
    output_docx = f"/home/sanel/personal-assistant-bot/study_guides/{filename_base}_Study_Guide.docx"
    
    # Check if we should append to save tokens instead of rebuilding
    if os.path.exists(output_md):
        print(f"Study guide for {topic} already exists. Running lightweight append-only update to save tokens...")
        
        internal_notes = ""
        notes_file = "/home/sanel/personal-assistant-bot/scrapers/source_cache/combined_summaries.txt"
        pdf_file = "/home/sanel/personal-assistant-bot/scrapers/source_cache/pdf_exports.txt"
        
        if os.path.exists(notes_file):
            with open(notes_file, "r") as f:
                internal_notes += f.read().replace('\x00', '').strip()
        if os.path.exists(pdf_file):
            with open(pdf_file, "r") as f:
                internal_notes += "\n\n" + f.read().replace('\x00', '').strip()
                
        if not internal_notes.strip():
            print("No new classroom notes to append. Skipping update.")
            return
            
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are an elite academic tutor. We are appending a new section to an existing master study guide on "{topic}".
Below are the LATEST classroom notes from today. 
Write a highly detailed new section titled "## 📅 Update: {today} - New Concepts" that perfectly synthesizes these new notes. 
DO NOT rewrite the entire study guide, ONLY output the new section to be appended to the bottom.

--- NEW CLASSROOM NOTES ---
{internal_notes}
"""
        import requests
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv("/home/sanel/personal-assistant-bot/.env")
            api_key = os.getenv("OPENROUTER_API_KEY")
            
        print("Calling OpenRouter (Owl-Alpha) for Delta-Append generation...")
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/SanelL112/Antigravity-Based-Assistant-Bot",
                    "X-Title": "Antigravity-Based-Assistant-Bot"
                },
                json={
                    "models": ["meta-llama/llama-3.3-70b-instruct:free", "nvidia/nemotron-3-ultra-550b-a55b:free"],
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=600
            )
            if response.status_code == 200:
                new_section = response.json()["choices"][0]["message"]["content"]
            else:
                print(f"OpenRouter returned {response.status_code}: {response.text}")
                new_section = ""
        except Exception as e:
            print(f"OpenRouter connection error: {e}")
            new_section = ""
        
        if new_section:
            # Clean up <thought> tags
            import re
            new_section = re.sub(r'<thought>.*?</thought>', '', new_section, flags=re.DOTALL).strip()
            
            with open(output_md, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n\n{new_section}\n")
            print(f"Successfully appended new concepts to {output_md}")
            result = True
        else:
            print("Failed to generate append section.")
            result = False
            
    else:
        print(f"No existing guide found for {topic}. Running full 10-chapter Mega Build...")
        result_text = generate_mega_guide(topic)
        if result_text:
            with open(output_md, "w", encoding="utf-8") as f:
                f.write(result_text)
            print(f"Successfully created study guide at {output_md}")
            result = True
        else:
            result = False

    if result:
        # 3. Convert to DOCX format
        print("Converting Markdown to DOCX format...")
        try:
            subprocess.run(["pandoc", output_md, "-o", output_docx], check=True)
            print(f"Successfully created Word document at {output_docx}")
            
            # 4. Automatically Sync to GitHub
            print("Pushing freshly generated study guide to GitHub...")
            subprocess.run(["git", "add", output_md, output_docx], check=True)
            subprocess.run(["git", "commit", "-m", f"docs: Nightly autonomous update of {filename_base} study guide"], check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"Nightly build for '{topic}' completely successfully!")
        except Exception as e:
            print(f"Post-processing pipeline failed: {e}")
    else:
        print(f"Failed to process study guide for {topic}.")

def main():
    print(f"=== Nightly Processor Started at {datetime.datetime.now()} ===")
    
    # Ensure the script is running in the correct directory for git tracking
    os.chdir("/home/sanel/personal-assistant-bot")
    
    # Ensure we have the latest updates
    subprocess.run(["git", "pull"], check=False)
    
    # 0. Sync New Google Classroom & Google Drive Files
    print("Executing Google Classroom & Drive Sync...")
    try:
        from scrapers.nightly_processor import run_nightly_job
        # Safely run the async sync job in the event loop
        asyncio.run(run_nightly_job(None, 8534649457))
        print("Successfully synced and downloaded all new queued PDFs and Docs into the memory bank.")
    except Exception as e:
        print(f"Warning: Failed to drain nightly sync queue: {e}")
    
    # 1. Separated Core Study Guides (Disciplinary Split)
    build_and_push("SAT Math and Geometry Master Guide")
    build_and_push("SAT Reading Comprehension Master Guide")
    build_and_push("SAT Writing and Grammar Master Guide")
    
    # 2. Load the Google Classroom PDF text to find dynamic topics
    pdf_path = "/home/sanel/personal-assistant-bot/scrapers/source_cache/pdf_exports.txt"
    pdf_text = ""
    if os.path.exists(pdf_path):
        with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
            pdf_text = f.read()
            # Strip null-bytes just to be safe
            pdf_text = pdf_text.replace('\x00', '')
    
    if pdf_text:
        # 3. Extract 3 dynamic topics based on the classroom material
        topics = extract_dynamic_topics(pdf_text, num_topics=3)
        print(f"Discovered dynamic topics for tonight's run: {topics}")
        
        # 4. Build a massive study guide for each discovered topic
        for dynamic_topic in topics:
            build_and_push(dynamic_topic)
    else:
        print("No Classroom PDF data found. Skipping dynamic topic generation.")
        
    print(f"=== Nightly Processor Finished at {datetime.datetime.now()} ===")

if __name__ == "__main__":
    import subprocess
    import time
    
    # Run the main processor
    main()
    
    # Nightly Build Complete: Stop Ollama to save RAM for the next day
    print("Nightly build complete. Stopping Ollama...")
    subprocess.run(['pkill', '-f', 'ollama serve'], check=False)

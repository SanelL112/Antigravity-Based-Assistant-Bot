import asyncio
import os
import sys
import datetime
import subprocess

# Ensure the parent directory is in sys.path
sys.path.append("/home/sanel/personal-assistant-bot")

from scrapers.mega_study_builder import generate_mega_guide
from ai_processor import call_agy

def extract_dynamic_topics(pdf_text: str, num_topics: int = 3) -> list:
    """Uses the AI to extract new, highly specific topics from the user's classroom notes."""
    prompt = f"""You are an intelligent topic extractor. Scan the following classroom notes and identify exactly {num_topics} distinct, highly specific academic topics or chapters that would make great study guides.
Respond ONLY with a comma-separated list of the topics. Do not include bullet points or numbers.
Example: Quadratic Equations, Civil War History, Biology Cell Structure

Notes:
{pdf_text[:15000]}
"""
    print("Extracting dynamic topics from classroom notes...")
    # Using 3600 timeout to respect the new timeout architecture
    result = call_agy(prompt, timeout=3600, model="flash")
    if result:
        topics = [t.strip() for t in result.split(",") if t.strip()]
        return topics[:num_topics]
    return ["General Mathematics", "Advanced Grammar", "Test Strategies"]

def build_and_push(topic: str):
    """Generates the massive study guide and automatically pushes it to GitHub."""
    print(f"\n==============================================")
    print(f"Starting Nightly Build Pipeline for: {topic}")
    print(f"==============================================\n")
    
    filename_base = topic.replace(" ", "_").replace("/", "_")
    
    # 1. Run the massive Editor-in-Chief pipeline
    result = generate_mega_guide(topic)
    
    if result:
        output_md = f"/home/sanel/personal-assistant-bot/{filename_base}_Study_Guide.md"
        output_docx = f"/home/sanel/personal-assistant-bot/{filename_base}_Study_Guide.docx"
        
        # 2. Write to Markdown file (always overwrite to prevent messy stacking)
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Successfully created study guide at {output_md}")
        
        # 3. Convert to DOCX format
        print("Converting Markdown to DOCX format...")
        try:
            subprocess.run(["pandoc", output_md, "-o", output_docx], check=True)
            print(f"Successfully created Word document at {output_docx}")
            
            # 4. Automatically Sync to GitHub
            print("Pushing freshly generated study guide to GitHub...")
            subprocess.run(["git", "add", output_md, output_docx], check=True)
            subprocess.run(["git", "commit", "-m", f"docs: Nightly autonomous build of {filename_base} study guide"], check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"Nightly build for '{topic}' completely successfully!")
        except Exception as e:
            print(f"Post-processing pipeline failed: {e}")
    else:
        print(f"Failed to generate study guide for {topic}.")

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
    main()

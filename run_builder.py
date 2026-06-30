import asyncio
import os
import sys

# Ensure the parent directory is in sys.path
sys.path.append("/home/sanel/personal-assistant-bot")

from scrapers.mega_study_builder import generate_mega_guide, logging
try:
    import telegram_logger
    telegram_logger.setup_telegram_logging()
except Exception as e:
    print(f"Could not load telegram logger: {e}")

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    import datetime
    import subprocess
    
    # Allow passing a dynamic topic via CLI, default to SAT
    topic = sys.argv[1] if len(sys.argv) > 1 else "Comprehensive SAT Exam Prep Guide"
    filename_base = topic.replace(" ", "_").replace("/", "_")
    
    print(f"Generating Mega Study Guide for: {topic}...")
    # The pdf_exports.txt is automatically pulled inside generate_mega_guide
    result = generate_mega_guide(topic)
    
    if result:
        output_md = f"/home/sanel/personal-assistant-bot/study_guides/{filename_base}_Study_Guide.md"
        output_docx = f"/home/sanel/personal-assistant-bot/{filename_base}_Study_Guide.docx"
        
        # Always overwrite the file so we don't end up with stacked/redundant versions
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Successfully created study guide at {output_md}")
        
        # Convert to DOCX using Pandoc
        print("Converting Markdown to DOCX format...")
        try:
            subprocess.run(["pandoc", output_md, "-o", output_docx], check=True)
            print(f"Successfully created Word document at {output_docx}")
            
            # Automatically push the generated study guides to GitHub
            print("Pushing generated study guides to GitHub...")
            os.chdir("/home/sanel/personal-assistant-bot")
            subprocess.run(["git", "add", output_md, output_docx], check=True)
            # Check if there are actually changes before committing
            status = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
            if status.returncode != 0:  # there are staged changes
                subprocess.run(["git", "commit", "-m", f"docs: Auto-update {filename_base} study guide"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("Successfully synced to GitHub!")
            else:
                print("No changes to commit — study guide is up to date.")
        except Exception as e:
            print(f"Post-processing pipeline failed: {e}")
    else:
        print("Failed to generate study guide.")

if __name__ == "__main__":
    asyncio.run(main())

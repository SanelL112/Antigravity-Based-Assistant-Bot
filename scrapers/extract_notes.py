import os
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
import subprocess

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanel/.local/bin/agy")

def transcribe_handwritten_pdf(pdf_path: str) -> str:
    """Uploads a PDF to Gemini Vision via Antigravity CLI and extracts handwritten notes."""
    logger.info(f"Asking Antigravity CLI to transcribe {pdf_path}...")
    
    prompt = (
        f"You are a multimodal AI vision tool. Use your view_file tool to read the PDF document at {pdf_path}. "
        "It contains handwritten mathematical and conceptual notes. Transcribe the handwriting exactly as it is written. "
        "Ignore doodles or illegible scribbles, but preserve all the core educational content and math formulas. "
        "Output ONLY the transcribed text."
    )
    
    try:
        # Run agy with --dangerously-skip-permissions so it can autonomously use view_file without prompting the user
        result = subprocess.run(
            [AGENTAPI_BIN, "--dangerously-skip-permissions", "--model", "pro", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"agy CLI failed: {result.stderr}")
            return f"Error transcribing PDF: {result.stderr}"
            
        # Clean up any ANSI color codes from agy output
        import re
        clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', result.stdout)
        clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()
        
        if not clean:
             return "Error: Antigravity CLI returned empty transcription."
             
        return clean
    except subprocess.TimeoutExpired:
        logger.error("Antigravity CLI timed out reading the PDF.")
        return "Error: Timed out while transcribing the PDF."
    except Exception as e:
        logger.error(f"Failed to transcribe PDF via agy: {e}")
        return f"Error transcribing PDF: {e}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(transcribe_handwritten_pdf(sys.argv[1]))

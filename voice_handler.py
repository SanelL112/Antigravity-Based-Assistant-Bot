"""
voice_handler.py — Voice message transcription via local Whisper.

When the user sends a voice note, download it, transcribe locally (PII-safe),
and feed the transcription into the chat pipeline.
"""
import os
import logging
import tempfile
import subprocess
from config import AGENTAPI_BIN

logger = logging.getLogger(__name__)


def transcribe_voice(file_path: str) -> str:
    """
    Transcribe a voice message locally. Tries whisper.cpp first (faster),
    falls back to agy with a multimodal model.
    """
    text = _try_whisper_cpp(file_path)
    if text:
        return text

    text = _try_whisper_cli(file_path)
    if text:
        return text

    text = _try_agy_audio(file_path)
    if text:
        return text

    return "Could not transcribe voice message. Try sending text instead."


def _try_whisper_cpp(file_path: str) -> str:
    """Try transcribing with whisper.cpp if available."""
    for path in ["/usr/local/bin/whisper-cpp", os.path.expanduser("~/.local/bin/whisper-cpp")]:
        if os.path.exists(path):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    wav_path = os.path.join(tmpdir, "audio.wav")
                    subprocess.run(
                        ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
                        capture_output=True, timeout=15
                    )
                    if not os.path.exists(wav_path):
                        continue
                    result = subprocess.run(
                        [path, "-m", "/usr/local/share/whisper/ggml-base.en.bin",
                         "-f", wav_path, "-l", "en"],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.returncode == 0:
                        text = result.stdout.strip()
                        if text and len(text) > 3:
                            logger.info(f"whisper.cpp transcribed {len(text)} chars")
                            return text
            except Exception as e:
                logger.warning(f"whisper.cpp failed: {e}")
    return ""


def _try_whisper_cli(file_path: str) -> str:
    """Try transcribing with openai-whisper if installed."""
    try:
        import whisper
        model = whisper.load_model("base", device="cpu")
        result = model.transcribe(file_path, language="en")
        text = result.get("text", "").strip()
        if text:
            logger.info(f"whisper CLI transcribed {len(text)} chars")
            return text
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"whisper CLI failed: {e}")
    return ""


def _try_agy_audio(file_path: str) -> str:
    """Fallback: use agy CLI with pro model for audio transcription."""
    prompt = (
        f"You are an audio transcription assistant. Transcribe the audio at {file_path}. "
        "Output ONLY the transcribed text, nothing else."
    )
    try:
        result = subprocess.run(
            [AGENTAPI_BIN, "--model", "pro", "--dangerously-skip-permissions", "--print", prompt],
            capture_output=True, text=True, timeout=180
        )
        text = result.stdout.strip()
        if text:
            import re
            clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)
            clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()
            logger.info(f"agy transcribed {len(clean)} chars")
            return clean
    except Exception as e:
        logger.warning(f"agy audio failed: {e}")
    return ""

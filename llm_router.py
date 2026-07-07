"""
llm_router.py — Unified LLM dispatch with cost tracking and smart fallbacks.

SECURITY MODEL:
- Local (Ollama Qwen2/Llama) and agy (flash/pro) handle ALL private data.
  These run on your server. Data never leaves.
- OpenRouter is ONLY called for general/academic content that is NOT PII.
  The privacy filter in main.py/ai_processor.py decides the route BEFORE calling this.

This module centralizes:
1. OpenRouter HTTP calls (replaces 4+ copies of `_call_or` across the codebase)
2. Cost tracking (Feature 10: /stats command)
3. Unified fallback chain: try primary → fallback → local failover
4. Response validation (replaces the sanity check LLM call)
"""
import os
import time
import json
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional
from config import (
    OPENROUTER_API_KEY, OR_DEFAULT_MODEL, OR_FALLBACK_MODEL,
    COST_LOG_FILE, AGENTAPI_BIN
)

logger = logging.getLogger(__name__)

# ── OpenRouter Session (connection pooling) ──────────────────────────────────
import httpx
import atexit

_or_session = None
_or_client = None

def _get_client() -> httpx.Client:
    global _or_client
    if _or_client is None:
        # Configure timeouts: connect=10s, read=60s, write=10s, pool=5s
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)
        _or_client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/SanelL112/Antigravity-Based-Assistant-Bot",
                "X-Title": "Personal Assistant Bot",
            },
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _or_client


def _cleanup_clients():
    """Clean up HTTP clients on exit."""
    global _or_client, _or_session
    if _or_client is not None:
        try:
            _or_client.close()
        except Exception:
            pass
        _or_client = None
    if _or_session is not None:
        try:
            _or_session.close()
        except Exception:
            pass
        _or_session = None

atexit.register(_cleanup_clients)


def _get_session() -> requests.Session:
    """Deprecated: use _get_client() for httpx instead."""
    global _or_session
    if _or_session is None:
        _or_session = requests.Session()
        _or_session.headers.update({
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/SanelL112/Antigravity-Based-Assistant-Bot",
            "X-Title": "Personal Assistant Bot",
        })
    return _or_session


# ── Cost Tracking (Feature 10) ───────────────────────────────────────────────
def load_cost_log() -> dict:
    try:
        with open(COST_LOG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": "", "total_usd": 0.0, "calls": [], "by_model": {}}


def save_cost_log(data: dict):
    """Atomic write for cost log (prevents corruption on crash)."""
    import tempfile
    try:
        fd, tmp_path = tempfile.mkstemp(dir=COST_LOG_FILE.parent, suffix='.tmp')
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, COST_LOG_FILE)
    except Exception:
        with open(COST_LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost. Free models and local = $0."""
    free_models = {
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "openrouter/owl-alpha:free",
    }
    paid_rates = {
        "openrouter/owl-alpha": (0.01, 0.03),  # ($/1K input, $/1K output)
    }
    if model in free_models:
        return 0.0
    rates = paid_rates.get(model, (0.0, 0.0))
    return (input_tokens / 1000 * rates[0]) + (output_tokens / 1000 * rates[1])


def log_call(model: str, task: str, prompt: str, result: str, duration_s: float):
    """Log an LLM call for cost tracking."""
    in_tokens = estimate_tokens(prompt)
    out_tokens = estimate_tokens(result)
    cost = estimate_cost_usd(model, in_tokens, out_tokens)

    log = load_cost_log()
    today = time.strftime("%Y-%m-%d")
    if log.get("date") != today:
        log = {"date": today, "total_usd": 0.0, "calls": [], "by_model": {}}

    log["total_usd"] += cost
    log.setdefault("calls", []).append({
        "time": time.strftime("%H:%M:%S"),
        "model": model,
        "task": task,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cost_usd": round(cost, 6),
        "duration_s": round(duration_s, 2),
    })
    # Keep last 500 calls to prevent bloat
    if len(log["calls"]) > 500:
        log["calls"] = log["calls"][-500:]

    log.setdefault("by_model", {})
    log["by_model"].setdefault(model, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0})
    log["by_model"][model]["calls"] += 1
    log["by_model"][model]["tokens_in"] += in_tokens
    log["by_model"][model]["tokens_out"] += out_tokens
    log["by_model"][model]["cost"] += cost

    save_cost_log(log)


def get_cost_summary():
    log = load_cost_log()
    today = time.strftime("%Y-%m-%d")

    if log.get("date") != today:
        return "📊 **Cost Dashboard**\nNo activity today yet."

    lines = [
        f"📊 **Cost Dashboard ({today})**",
        f"Total: `${log['total_usd']:.4f}` | {len(log.get('calls', []))} calls",
        "",
        "**By Model:**",
    ]
    for model, stats in log.get("by_model", {}).items():
        lines.append(f"  `{model}`: {stats['calls']} calls, "
                     f"{stats['tokens_in'] + stats['tokens_out']:,} tokens, "
                     f"${stats['cost']:.4f}")
    return "\n".join(lines)


# ── Response Validation (replaces sanity check LLM call) ─────────────────────
FAIL_PHRASES = ["i cannot", "i'm sorry", "i don't know", "as an ai", "unable to", "i apologize"]


def is_valid_response(text: str) -> bool:
    """Heuristic response validation — no LLM call needed."""
    if not text or len(text.strip()) < 5:
        return False
    # Detect system prompt regurgitation
    if text.startswith("You are a powerful personal assistant") or \
       text.startswith("You are Sanel"):
        return False
    # Short refusals
    if len(text) < 100 and any(p in text.lower()[:50] for p in FAIL_PHRASES):
        return False
    return True


# ── OpenRouter Unified Caller ────────────────────────────────────────────────
def call_openrouter(
    model: str,
    prompt: str,
    task: str = "general",
    max_tokens: int = 4000,
    system_prompt: str = "",
    fallback_chain: list = None,
    timeout: int = 120,
    stream_to_status=None,   # optional: (context, chat_id, status_msg) for streaming edits
) -> str:
    """
    Unified OpenRouter caller with retry, fallback, cost tracking.

    SECURITY: Only call this with NON-PII, general/academic prompts.
    Private data should go through call_agy() or call_ollama() instead.

    Args:
        model: OpenRouter model ID (e.g. "openrouter/owl-alpha")
        prompt: The user message
        task: Label for cost tracking (e.g. "study-guide", "watchdog", "chat")
        system_prompt: Optional system message
        fallback_chain: List of fallback model IDs if primary fails
        timeout: HTTP timeout in seconds
        stream_to_status: Optional (context, chat_id, status_msg) for live typing updates

    Returns:
        Generated text string
    """
    chain = [model] + (fallback_chain or [])
    all_models = set(chain)

    for i, m in enumerate(chain):
        start = time.time()
        try:
            result = _do_call(m, prompt, task, max_tokens, system_prompt, timeout,
                              stream_to_status if i == 0 else None)
            duration = time.time() - start

            if is_valid_response(result):
                log_call(m, task, prompt, result, duration)
                return result
            else:
                logger.warning(f"Model {m} returned invalid response, trying fallback...")
                log_call(m, task, prompt, "(invalid)", duration)
                continue

        except Exception as e:
            duration = time.time() - start
            logger.warning(f"Model: {e} ({duration:.1f}s)")
            log_call(m, task, prompt, f"(error: {e})", duration)
            continue

    return "⚠️ All models failed to generate a response. Please try again."


def _do_call(
    model: str,
    prompt: str,
    task: str,
    max_tokens: int,
    system_prompt: str,
    timeout: int,
    stream_to_status: Optional[tuple],
) -> str:
    """Execute a single OpenRouter API call. Supports streaming with live status updates."""
    client = _get_client()
    from utils import scrub_pii

    # SECURITY: Scrub PII from all cloud-bound prompts
    scrubbed_prompt = scrub_pii(prompt)
    if scrubbed_prompt != prompt:
        logger.info(f"scrubbed PII from {task} prompt")
    if system_prompt:
        scrubbed_system = scrub_pii(system_prompt)
    else:
        scrubbed_system = ""

    messages = []
    if scrubbed_system:
        messages.append({"role": "system", "content": scrubbed_system})
    messages.append({"role": "user", "content": scrubbed_prompt})

    # Streaming path (for chat responses where we show typing)
    if stream_to_status:
        return _streaming_call(client, model, messages, task, max_tokens, timeout, stream_to_status)
    else:
        # Non-streaming (simpler, for everything else)
        resp = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            choice = resp.json()["choices"][0]
            text = choice["message"]["content"].strip()
            # Detect truncation
            if choice.get("finish_reason") == "length":
                text += "\n\n⚠️ Response was truncated due to output length limits."
            return text
        else:
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

def _streaming_call(client, model, messages, task, max_tokens, timeout, stream_to_status):
    """Fallback streaming implementation if not using async HTTPX."""
    # stream_to_status is (context, chat_id, status_msg, loop)
    context, chat_id, status_msg, main_loop = stream_to_status
    full_response = ""
    current_thought = ""
    in_thought = False
    last_edit = 0

    # Use httpx streaming with proper timeout
    try:
        resp = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": True,
            },
            timeout=timeout,
        )
    except httpx.TimeoutException:
        raise Exception(f"OpenRouter streaming timeout after {timeout}s")

    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")

    try:
        for line in resp.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            data = line[6:]
            if data == b"[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_response += content

                    if "<thought>" in full_response and "</thought>" not in full_response:
                        in_thought = True
                        current_thought = full_response.split("<thought>")[-1]
                    elif "</thought>" in full_response:
                        in_thought = False

                    now = time.time()
                    if now - last_edit > 1.5 and status_msg and context:
                        last_edit = now
                        try:
                            import asyncio
                            coro = None
                            if in_thought:
                                coro = context.bot.edit_message_text(
                                    chat_id=chat_id, message_id=status_msg.message_id,
                                    text=f"🧠 **Thinking...**\n_{current_thought[-400:].strip()}_", parse_mode="Markdown"
                                )
                            else:
                                final_text = full_response.split("</thought>")[-1] if "</thought>" in full_response else full_response
                                disp = final_text[-800:].strip()
                                if disp:
                                    coro = context.bot.edit_message_text(
                                        chat_id=chat_id, message_id=status_msg.message_id,
                                        text=f"✍️ **Typing...**\n{disp}"
                                    )
                            if coro:
                                try:
                                    import asyncio
                                    asyncio.run_coroutine_threadsafe(coro, main_loop)
                                except Exception:
                                    pass # Ignore if loop is dead or coro fails
                        except Exception:
                            pass
            except Exception:
                continue
    finally:
        # Ensure response is closed to release connection back to pool
        resp.close()

    if "</thought>" in full_response:
        return full_response.split("</thought>")[-1].strip()
    return full_response.strip()


# ── Local LLM Wrappers (PII-safe, never leaves server) ──────────────────────
def call_ollama(prompt: str, model: str = "hf.co/Qwen/Qwen2-0.5B-Instruct-GGUF:latest",
                timeout: int = 30) -> str:
    """Call local Ollama model. Safe for PII — runs entirely on your server."""
    try:
        import httpx
        # Use proper httpx timeout with all 4 parameters
        httpx_timeout = httpx.Timeout(connect=10.0, read=float(timeout), write=10.0, pool=5.0)
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
            timeout=httpx_timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        return ""
    except httpx.TimeoutException:
        logger.error(f"Ollama call timed out after {timeout}s")
        return ""
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return ""


def call_agy_local(prompt: str, model: str = "flash", timeout: int = 180) -> str:
    """
    Call local agy CLI via PTY. Safe for PII — runs entirely on your server.
    This replaces the duplicate implementations across the codebase.
    """
    import pty
    import select
    import re

    def _run_model(target_model: str) -> str:
        master = -1
        proc = None
        try:
            master, slave = pty.openpty()
            proc = subprocess.Popen(
                [AGENTAPI_BIN, "--model", target_model, "--dangerously-skip-permissions", "--print", prompt],
                stdin=slave, stdout=slave, stderr=slave,
                close_fds=True
            )
            os.close(slave)

            output_chunks = []
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    r, _, _ = select.select([master], [], [], 1.0)
                    if r:
                        try:
                            chunk = os.read(master, 4096)
                            output_chunks.append(chunk)
                        except OSError:
                            break
                except Exception:
                    break
                if proc.poll() is not None:
                    try:
                        while True:
                            r, _, _ = select.select([master], [], [], 0.2)
                            if r:
                                chunk = os.read(master, 4096)
                                output_chunks.append(chunk)
                            else:
                                break
                    except OSError:
                        pass
                    break

            try:
                proc.wait(timeout=5)
            except Exception:
                pass

            raw = b"".join(output_chunks).decode("utf-8", errors="replace")
            clean = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', raw)
            clean = clean.replace('\r\n', '\n').replace('\r', '\n').strip()

            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
                return ""

            return clean

        except Exception as e:
            logger.error(f"agy pty error ({target_model}): {e}")
            return ""
        finally:
            if master >= 0:
                try:
                    os.close(master)
                except OSError:
                    pass
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    import subprocess
    result = _run_model(model)
    if not result and model != "pro":
        logger.warning(f"agy {model} failed, falling back to pro...")
        result = _run_model("pro")
    return result


# ── Utility ──────────────────────────────────────────────────────────────────
def response_cache_key(model: str, prompt: str) -> str:
    return hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()


def is_ollama_healthy() -> bool:
    """Check if Ollama is running and responsive."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def is_agy_healthy(model: str = "flash") -> bool:
    """Check if agy CLI is functional."""
    import subprocess
    try:
        result = subprocess.run(
            [AGENTAPI_BIN, "--model", model, "--print", "Say OK"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        return False


# ── Health Check on Import ─────────────────────────────────────────────────
# Removed to speed up import time. Health checks should be called lazily.

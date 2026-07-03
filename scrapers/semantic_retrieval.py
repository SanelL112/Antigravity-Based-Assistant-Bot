"""
Semantic Retrieval — finds the most relevant chunks from the embedding index.

At query time:
1. Embed the user's query via Ollama (one call, ~100ms on CPU)
2. Compute cosine similarity against all stored vectors (numpy, <1ms for ~5K chunks)
3. Return top-K most relevant text chunks

Falls back to the old tail-truncation approach if:
- The embedding index doesn't exist yet
- Ollama is not running (and can't be started briefly)
"""

import os
import logging
import subprocess

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [retrieval] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, "embedding_data", "embedding_index.npz")
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
DIM = 768

# How many chunks to inject into the bot's prompt
DEFAULT_TOP_K = 8
# Maximum total characters of retrieved context (don't blow up the prompt)
MAX_CONTEXT_CHARS = 12000


# ── Index loading (lazy, cached) ──────────────────────────────────────────────

_index_cache = None


def _load_index() -> tuple[np.ndarray, list[str], list[str]] | None:
    """Load the embedding index from disk. Cached after first load."""
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not os.path.exists(INDEX_PATH):
        return None
    try:
        data = np.load(INDEX_PATH, allow_pickle=True)
        vectors = data["vectors"]
        chunks = data["chunks"].tolist()
        sources = data["sources"].tolist()
        if len(vectors) == 0:
            return None
        # Normalize vectors once for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
        _index_cache = (vectors, chunks, sources)
        logger.info(f"Loaded index: {len(chunks)} chunks, {vectors.shape}")
        return _index_cache
    except Exception as e:
        logger.warning(f"Failed to load index: {e}")
        return None


def invalidate_cache():
    """Call this after the index is rebuilt."""
    global _index_cache
    _index_cache = None


# ── Query embedding ───────────────────────────────────────────────────────────
import httpx

# Shared httpx client for connection pooling
_ollama_client = None

def _get_ollama_client() -> httpx.Client:
    global _ollama_client
    if _ollama_client is None:
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)
        _ollama_client = httpx.Client(timeout=timeout)
    return _ollama_client


def _ollama_is_running() -> bool:
    """Check if Ollama is reachable."""
    try:
        client = _get_ollama_client()
        resp = client.get(f"{OLLAMA_URL}/api/tags")
        return resp.status_code == 200
    except Exception:
        return False


def _start_ollama():
    """Try to start Ollama if it's not running. Non-blocking."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        for _ in range(10):  # wait up to 10s
            time.sleep(1)
            if _ollama_is_running():
                return True
    except Exception:
        pass
    return False


def embed_query(query: str) -> np.ndarray | None:
    """Embed a single query string via Ollama. Returns float32 vector of shape (DIM,).
    Starts Ollama if needed. Returns None if embedding fails.
    """
    # Try to start Ollama if not running
    if not _ollama_is_running():
        logger.info("Ollama not running, attempting to start...")
        if not _start_ollama():
            logger.warning("Could not start Ollama, falling back to non-semantic retrieval")
            return None

    try:
        client = _get_ollama_client()
        resp = client.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": query},
        )
        if resp.status_code != 200:
            logger.warning(f"Embedding failed: {resp.status_code}")
            return None
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings and len(embeddings[0]) == DIM:
            vec = np.array(embeddings[0], dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec
    except httpx.TimeoutException:
        logger.warning(f"Query embedding timeout")
        return None
    except Exception as e:
        logger.warning(f"Query embedding error: {e}")
    return None


# ── Retrieval ──────────────────────────────────────────────────────────────────

def semantic_search(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Search the embedding index for chunks most similar to the query.

    Returns list of {"text": str, "source": str, "score": float},
    sorted by descending similarity.
    """
    index = _load_index()
    if index is None:
        return []

    vectors, chunks, sources = index

    query_vec = embed_query(query)
    if query_vec is None:
        return []

    # Cosine similarity (vectors already normalized)
    scores = vectors @ query_vec  # dot product == cosine similarity for unit vectors

    # Get top-K
    top_k = min(top_k, len(chunks))
    top_indices = np.argpartition(scores, -top_k)[-top_k:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

    results = []
    for idx in top_indices:
        results.append({
            "text": chunks[idx],
            "source": sources[idx],
            "score": float(scores[idx]),
        })

    return results


def get_context_for_prompt(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Get formatted context string for injection into the bot's system prompt.

    This is the main entry point called from main.py.
    Returns a formatted string of relevant chunks, or empty string if
    semantic retrieval is unavailable.
    """
    results = semantic_search(query, top_k=top_k)
    if not results:
        return ""

    context_parts = []
    total_chars = 0

    for r in results:
        source_name = os.path.basename(r["source"])
        score_pct = r["score"] * 100
        entry = f"[{source_name} (relevance: {score_pct:.0f}%)]\n{r['text']}"
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(entry)
        total_chars += len(entry)

    if not context_parts:
        return ""

    header = f"=== SEMANTIC RETRIEVAL (top {len(context_parts)} chunks for: \"{query[:80]}\") ==="
    return header + "\n\n" + "\n\n---\n\n".join(context_parts) + "\n\n=== END RETRIEVAL ==="


# ── Fallback: old tail-truncation method ─────────────────────────────────────────

def get_fallback_context() -> tuple[str, str]:
    """Return (brain_context, digest_context) using the old tail-truncation method.
    Used when semantic retrieval is unavailable.
    """
    brain_context = "No offline memory consolidated yet."
    digest_context = "No recent data available."

    brain_file = os.path.join(BASE_DIR, "curated_brain.md")
    if os.path.exists(brain_file):
        with open(brain_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            brain_context = content[-15000:] if len(content) > 15000 else content

    mega_file = os.path.join(BASE_DIR, "mega_index.md")
    if os.path.exists(mega_file):
        with open(mega_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            # Combine: last 5K of mega index instead of separate
            if len(content) > 5000:
                brain_context += "\n\n--- Recent Index Entries ---\n" + content[-5000:]
            else:
                brain_context += "\n\n--- Recent Index Entries ---\n" + content

    digest_file = os.path.join(BASE_DIR, "latest_digest.txt")
    if os.path.exists(digest_file):
        with open(digest_file, "r", encoding="utf-8", errors="replace") as f:
            digest_context = f.read()

    return brain_context, digest_context

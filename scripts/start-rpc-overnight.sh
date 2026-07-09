#!/usr/bin/env bash
# =============================================================================
# start-rpc-overnight.sh
# Starts a llama-server with RPC layer offloading to Orange Pi 5 for
# overnight batch inference (7B+ models split across Server + Orange Pi).
#
# Usage:
#   ./scripts/start-rpc-overnight.sh           # Start with defaults
#   ./scripts/start-rpc-overnight.sh --stop    # Stop the RPC server
#   ./scripts/start-rpc-overnight.sh --status  # Check if running
#
# Architecture:
#   Server (5.7GB) ← llama-server --rpc → Orange Pi (3.8GB)
#   Layers 1-14 run on Server, layers 15-28 run on Orange Pi.
#   Combined ~9.5GB = enough for 7B Q4_K_M.
#   Speed: ~3-8 tok/s (Ethernet-bound), fine for batch.
#
# Prerequisites (one-time):
#   1. Orange Pi running: ggml-rpc-server --host 0.0.0.0 --port 50052
#   2. Model pulled: ollama pull qwen2.5:7b-instruct-q4_K_M
#   3. llama.cpp installed: /usr/local/bin/llama-server (built with GGML_RPC=ON)
#   4. Orange Pi: systemctl enable --now rpc-server  (persistent across reboots)
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
RPC_WORKER="${RPC_WORKER:-10.10.10.2:50052}"
RPC_PORT="${RPC_PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-4096}"
THREADS="${THREADS:-2}"

# Find the largest matching GGUF model (by size, not name — blob filenames are hashes)
MODEL_DIR="${MODEL_DIR:-$HOME/.ollama/models/blobs}"
MODEL_GLOB="${MODEL_GLOB:-sha256-*qwen2.5*}"
MODEL_PATH=$(find "$MODEL_DIR" -name "$MODEL_GLOB" -type f 2>/dev/null \
    | xargs -r ls -1S | head -1)

# ── Commands ─────────────────────────────────────────────────────────────────

# Use Python for port checks (nc not available on all systems)
check_port() {
    python3 -c "import socket; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('$1',$2)); s.close(); exit(r)" 2>/dev/null
}

case "${1:-start}" in
    --stop|stop)
        echo "=== Stopping RPC llama-server ==="
        pkill -f "llama-server" 2>/dev/null && echo "  ✅ Stopped." || echo "  Not running."
        ;;
    --status|status)
        if curl -sf "http://localhost:${RPC_PORT}/health" >/dev/null 2>&1; then
            echo "✅ RPC llama-server is RUNNING on port ${RPC_PORT}"
            echo "   Health: $(curl -s http://localhost:${RPC_PORT}/health 2>/dev/null || echo 'unknown')"
        else
            echo "❌ RPC llama-server is NOT running on port ${RPC_PORT}"
        fi

        echo ""
        echo "=== Orange Pi RPC worker (${RPC_WORKER}) ==="
        if check_port "${RPC_WORKER%:*}" "${RPC_WORKER##*:}"; then
            echo "✅ ggml-rpc-server reachable on ${RPC_WORKER}"
        else
            echo "❌ Cannot reach ggml-rpc-server on ${RPC_WORKER}"
        fi

        echo ""
        echo "=== Models available ==="
        if [ -d "$MODEL_DIR" ]; then
            find "$MODEL_DIR" -name "sha256-*" -type f 2>/dev/null \
                | while read -r f; do
                    size=$(du -h "$f" 2>/dev/null | cut -f1)
                    echo "   $size  $f"
                  done
        else
            echo "   No models found in $MODEL_DIR"
        fi
        ;;
    *)
        echo "=== Starting RPC llama-server for overnight batch inference ==="

        # Check prerequisites
        if ! command -v llama-server &>/dev/null; then
            echo "❌ llama-server not found in PATH."
            echo "   Install: brew install llama.cpp  (Mac)"
            echo "         or: apt install llama.cpp   (Linux)"
            exit 1
        fi

        if [ -z "$MODEL_PATH" ]; then
            echo "❌ No model found matching ${MODEL_DIR}/${MODEL_GLOB}"
            echo "   Pull one first: ollama pull qwen2.5:7b-instruct-q4_K_M"
            exit 1
        fi

        if ! check_port "${RPC_WORKER%:*}" "${RPC_WORKER##*:}"; then
            echo "⚠️  WARNING: Cannot reach Orange Pi RPC worker at ${RPC_WORKER}"
            echo "   Make sure ggml-rpc-server is running on the Orange Pi:"
            echo "   ssh root@10.10.10.2 'systemctl start rpc-server'"
            echo ""
            echo "   Continuing anyway — model will run entirely on this machine."
            echo "   If it OOMs, start the Orange Pi RPC worker first."
        fi

        echo "   Model: $MODEL_PATH"
        echo "   Size:  $(du -h "$MODEL_PATH" | cut -f1)"
        echo "   Worker: ${RPC_WORKER}"
        echo "   Port: ${RPC_PORT}"
        echo ""

        # Kill any existing instance
        pkill -f "llama-server" 2>/dev/null || true
        sleep 1

        # Start llama-server with RPC (runs in foreground)
        echo "   Starting llama-server..."
        # Note: -ngl removed — server has no GPU. RPC splits layers via --rpc flag.
        # Both server (GCC 14 x86_64) and Orange Pi (GCC 15 aarch64) binaries work
        # despite compiler version differences — the RPC protocol is arch-agnostic.
        exec llama-server \
            -m "$MODEL_PATH" \
            --rpc "$RPC_WORKER" \
            --host 127.0.0.1 \
            --port "$RPC_PORT" \
            -c "$CTX_SIZE" \
            -t "$THREADS"
        ;;
esac

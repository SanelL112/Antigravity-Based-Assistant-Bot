#!/usr/bin/env bash
# =============================================================================
# start-rpc-overnight.sh
# Starts a llama-server with RPC layer offloading to Orange Pi 5 for
# overnight batch inference (7B+ models split across Server + Orange Pi).
#
# Usage:
#   ./scripts/start-rpc-overnight.sh [--14b]  # Start with 7B (default) or 14B
#   ./scripts/start-rpc-overnight.sh --stop   # Stop the RPC server
#   ./scripts/start-rpc-overnight.sh --status # Check if running
#   ./scripts/start-rpc-overnight.sh --solo   # Start WITHOUT RPC (solo mode)
#
# Architecture:
#   Server (5.7GB) ← llama-server --rpc → Orange Pi (3.8GB)
#   Speed: ~3-8 tok/s for 7B (Ethernet-bound), fine for batch.
#   14B may OOM on Orange Pi (3.8GB) — script auto-detects and falls back.
#
# OOM Protection:
#   - Checks free RAM on both machines before starting.
#   - Falls back to solo mode if Orange Pi has insufficient RAM.
#   - Monitors RSS during operation; kills + restarts if exceeding threshold.
#   - Drops caches before starting to maximize available RAM.
#
# Prerequisites (one-time):
#   1. Orange Pi running: ggml-rpc-server --host 0.0.0.0 --port 50052
#   2. Model pulled: ollama pull qwen2.5:7b-instruct-q4_K_M (or 14b)
#   3. llama.cpp installed: /usr/local/bin/llama-server (built with GGML_RPC=ON)
#   4. Orange Pi systemd: systemctl enable --now rpc-server
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
RPC_WORKER="${RPC_WORKER:-10.10.10.2:50052}"
RPC_PORT="${RPC_PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-2048}"
THREADS="${THREADS:-2}"

# OOM thresholds (MB)
SERVER_MIN_FREE_MB="${SERVER_MIN_FREE_MB:-1200}"
WORKER_MIN_FREE_MB="${WORKER_MIN_FREE_MB:-700}"
MAX_RSS_MB="${MAX_RSS_MB:-3800}"          # Kill if llama-server RSS exceeds this
RSS_CHECK_INTERVAL="${RSS_CHECK_INTERVAL:-60}"  # Seconds between RSS checks

MODEL_DIR="${MODEL_DIR:-$HOME/.ollama/models/blobs}"

# ── Helper functions ─────────────────────────────────────────────────────────

# Check if a TCP port is open
check_port() {
    python3 -c "import socket; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('$1',$2)); s.close(); exit(r)" 2>/dev/null
}

# Get available memory in MB
get_avail_mb() {
    awk '/MemAvailable:/{print int($2/1024)}' /proc/meminfo 2>/dev/null || echo "0"
}

# Get llama-server RSS in MB by PID file (avoids pgrep matching wrong process)
LLAMA_PID_FILE="${LLAMA_PID_FILE:-/tmp/llama-server.pid}"

get_rss_mb() {
    if [ -f "$LLAMA_PID_FILE" ]; then
        local pid
        pid=$(cat "$LLAMA_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            awk '/^VmRSS:/{print int($2/1024)}' "/proc/$pid/status" 2>/dev/null || echo "0"
            return
        fi
    fi
    echo "0"
}

# Get Orange Pi available memory via SSH
get_worker_avail_mb() {
    local host="${RPC_WORKER%:*}"
    ssh -o ConnectTimeout=5 "root@${host}" \
        "awk '/MemAvailable:/{print int(\$2/1024)}' /proc/meminfo" 2>/dev/null || echo "-1"
}

# Find model by size/pattern
find_model() {
    local glob_pattern="${1:-sha256-*}"
    find "$MODEL_DIR" -name "$glob_pattern" -type f -not -name "*partial" 2>/dev/null \
        | xargs -r ls -1S | head -1
}

# ── OOM-aware start ──────────────────────────────────────────────────────────

start_rpc_server() {
    local model_path="$1"
    local use_rpc="$2"  # "yes" or "no"

    echo "=== Starting llama-server for overnight inference ==="
    echo "   Model:  $(basename "$model_path")"
    echo "   Size:   $(du -h "$model_path" | cut -f1)"
    echo "   Port:   ${RPC_PORT}"
    echo "   RPC:    ${use_rpc}"
    echo ""

    # ── Pre-flight memory checks ──────────────────────────────────────────
    local server_avail
    server_avail=$(get_avail_mb)
    echo "   Server RAM: ${server_avail}MB available"

    if [ "$server_avail" -lt "$SERVER_MIN_FREE_MB" ]; then
        echo "   ⚠️  WARNING: Server has only ${server_avail}MB free (need ${SERVER_MIN_FREE_MB}MB)"
        echo "   Dropping caches to free memory..."
        echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        sleep 2
        server_avail=$(get_avail_mb)
        echo "   Server RAM after cache drop: ${server_avail}MB available"
    fi

    # Check Orange Pi if using RPC
    if [ "$use_rpc" = "yes" ]; then
        local worker_avail
        worker_avail=$(get_worker_avail_mb)
        echo "   Orange Pi RAM: ${worker_avail}MB available"

        if [ "$worker_avail" = "-1" ]; then
            echo "   ⚠️  WARNING: Cannot reach Orange Pi for memory check"
            echo "   Continuing with RPC — will fall back to solo if worker unreachable"
        elif [ "$worker_avail" -lt "$WORKER_MIN_FREE_MB" ]; then
            echo "   ❌ Orange Pi has only ${worker_avail}MB free (need ${WORKER_MIN_FREE_MB}MB)"
            echo "   Auto-falling back to SOLO mode (no RPC)."
            use_rpc="no"
            echo "   Try: ssh root@10.10.10.2 'systemctl restart rpc-server; echo 3 > /proc/sys/vm/drop_caches'"
        fi
    fi

    # ── Kill any existing instance ─────────────────────────────────────────
    pkill -f "llama-server" 2>/dev/null || true
    sleep 1

    # ── Build command ──────────────────────────────────────────────────────
    local cmd_args=(
        llama-server
        -m "$model_path"
        --host 127.0.0.1
        --port "$RPC_PORT"
        -c "$CTX_SIZE"
        -t "$THREADS"
        --no-mmap
    )

    if [ "$use_rpc" = "yes" ]; then
        cmd_args+=(--rpc "$RPC_WORKER")
        echo "   Mode: RPC (Server + Orange Pi)"
    else
        echo "   Mode: SOLO (server only — no Orange Pi)"
    fi

    echo "   Starting llama-server..."
    "${cmd_args[@]}" > /tmp/llama-server.log 2>&1 &
    local pid=$!
    echo "$pid" > "$LLAMA_PID_FILE"

    # Trap to clean up RSS monitor on any exit (Ctrl+C, SIGTERM, etc.)
    local monitor_pid=""
    trap 'kill "$monitor_pid" 2>/dev/null; rm -f "$LLAMA_PID_FILE"; echo "   Cleaned up."' EXIT INT TERM

    # ── Wait for health check ──────────────────────────────────────────────
    echo "   Waiting for server to become healthy (up to 120s)..."
    local healthy=0
    for i in $(seq 1 60); do
        sleep 2
        if curl -sf "http://localhost:${RPC_PORT}/health" >/dev/null 2>&1; then
            echo "   ✅ Healthy after $((i*2))s (PID $pid)"
            healthy=1
            break
        fi

        # Check if process died
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "   ❌ Process died during startup. Check /tmp/llama-server.log"
            echo "   Last 5 log lines:"
            tail -5 /tmp/llama-server.log 2>/dev/null || true
            return 1
        fi
        printf .
    done

    if [ "$healthy" -eq 0 ]; then
        echo "   ❌ Failed to become healthy within 120s"
        echo "   Last 10 log lines:"
        tail -10 /tmp/llama-server.log 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
        return 1
    fi

    # ── Background RSS monitor ─────────────────────────────────────────────
    (
        while kill -0 "$pid" 2>/dev/null; do
            sleep "$RSS_CHECK_INTERVAL"
            local rss
            rss=$(get_rss_mb)
            if [ "$rss" -gt "$MAX_RSS_MB" ]; then
                echo "[$(date '+%H:%M:%S')] ⚠️  RSS ${rss}MB exceeds limit ${MAX_RSS_MB}MB — killing to prevent OOM"
                kill "$pid" 2>/dev/null || true
                break
            fi
            echo "[$(date '+%H:%M:%S')] RSS: ${rss}MB / ${MAX_RSS_MB}MB limit"
        done
    ) &
    monitor_pid=$!

    # ── Wait for server to exit (or be killed) ─────────────────────────────
    echo "   RPC server running (PID $pid). RSS monitor: PID $monitor_pid."
    echo "   Press Ctrl+C to stop, or send SIGTERM to PID $pid."
    wait "$pid" 2>/dev/null || true
    echo "   llama-server exited."
}


# ── Main dispatch ────────────────────────────────────────────────────────────

case "${1:-start}" in
    --stop|stop)
        echo "=== Stopping RPC llama-server ==="
        pkill -f "llama-server" 2>/dev/null && echo "  ✅ Stopped." || echo "  Not running."
        ;;

    --status|status)
        if curl -sf "http://localhost:${RPC_PORT}/health" >/dev/null 2>&1; then
            local health
            health=$(curl -s "http://localhost:${RPC_PORT}/health" 2>/dev/null || echo "unknown")
            echo "✅ RPC llama-server is RUNNING on port ${RPC_PORT}"
            echo "   Health: $health"
            local rss
            rss=$(get_rss_mb)
            echo "   RSS:    ${rss}MB"
            echo "   Server RAM: $(get_avail_mb)MB available"
        else
            echo "❌ RPC llama-server is NOT running on port ${RPC_PORT}"
        fi

        echo ""
        echo "=== Orange Pi RPC worker (${RPC_WORKER}) ==="
        if check_port "${RPC_WORKER%:*}" "${RPC_WORKER##*:}"; then
            local worker_avail
            worker_avail=$(get_worker_avail_mb)
            echo "✅ ggml-rpc-server reachable (${worker_avail}MB available)"
        else
            echo "❌ Cannot reach ggml-rpc-server on ${RPC_WORKER}"
        fi

        echo ""
        echo "=== Models available ==="
        if [ -d "$MODEL_DIR" ]; then
            find "$MODEL_DIR" -name "sha256-*" -type f -not -name "*partial" 2>/dev/null \
                | while read -r f; do
                    size=$(du -h "$f" 2>/dev/null | cut -f1)
                    echo "   $size  $(basename "$f")"
                  done
        else
            echo "   No models found in $MODEL_DIR"
        fi
        ;;

    --solo|solo)
        # Start without RPC (solo mode on server only)
        MODEL_PATH=$(find_model "sha256-*")
        if [ -z "$MODEL_PATH" ]; then
            echo "❌ No model found in ${MODEL_DIR}"
            echo "   Pull one: ollama pull qwen2.5:7b-instruct-q4_K_M"
            exit 1
        fi
        start_rpc_server "$MODEL_PATH" "no"
        ;;

    --14b|14b)
        # Start with 14B model (larger, more likely to need RPC)
        MODEL_PATH=$(find_model "sha256-*")
        # Prefer the largest model (14B is ~8.4GB)
        if [ -z "$MODEL_PATH" ]; then
            echo "❌ No model found in ${MODEL_DIR}"
            echo "   Pull one: ollama pull qwen2.5:14b"
            exit 1
        fi
        MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
        echo "=== Selected largest model: $(basename "$MODEL_PATH") (${MODEL_SIZE}) ==="
        start_rpc_server "$MODEL_PATH" "yes"
        ;;

    *)
        # Default: start with 7B-ish model (filter for smaller models)
        MODEL_PATH=$(find_model "sha256-*")
        if [ -z "$MODEL_PATH" ]; then
            echo "❌ No model found in ${MODEL_DIR}"
            echo "   Pull one: ollama pull qwen2.5:7b-instruct-q4_K_M"
            exit 1
        fi
        start_rpc_server "$MODEL_PATH" "yes"
        ;;
esac

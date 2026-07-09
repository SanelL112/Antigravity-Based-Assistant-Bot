#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# llama.cpp RPC Runbook — Orange Pi 5 + i5-3210M Laptop
# ──────────────────────────────────────────────────────────────────────────────
#
# Purpose:  Run distributed inference by splitting a GGUF model's layers
#           across both machines over Gigabit Ethernet (942 Mbits/sec).
#
# Architecture:
#   ┌──────────────────────┐       ┌──────────────────────────┐
#   │  Orange Pi 5 (RK3588) │◄─────►│  Laptop (i5-3210M, 5.7G) │
#   │  ARM64, 3.8 GB RAM   │  RPC  │  x86_64, 5.7 GB RAM      │
#   │  IP: 10.10.10.2       │       │  IP: 10.10.10.1           │
#   │  Role: PRIMARY         │       │  Role: WORKER             │
#   │  Port: 8081 (API)     │       │  Port: 50052 (RPC)        │
#   └──────────────────────┘       └──────────────────────────┘
#
# Requirements:
#   - llama-server with RPC on BOTH machines (see "Binary Setup" below)
#   - Same GGUF model at same path on BOTH machines (see "Model Setup")
#   - Gigabit Ethernet between them (ssh root@10.10.10.2 must work)
#
# ── Model Compatibility ──────────────────────────────────────────────────────
#   Model Size │ Combined RAM Needed │ Viable? │ Notes
#   ───────────│────────────────────│─────────│────────────────────
#   0.5B       │ ~500 MB             │ ✅ Yes  │ Fast, reliable
#   1.5B       │ ~1.0 GB             │ ✅ Yes  │ Comfortable split
#   3B  Q4_K_M │ ~2.0 GB             │ ⚠️ Edge │ Must stop Ollama first
#   7B  Q4_K_M │ ~4.5 GB             │ ❌ No   │ Exceeds combined RAM
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Config ───────────────────────────────────────────────────────────────────
LAPTOP_IP="10.10.10.1"
LAPTOP_RPC_PORT="50052"
LAPTOP_LLAMA_SERVER="/usr/local/bin/llama-server"
LAPTOP_MODEL="/root/models/qwen2.5-3b-instruct-q4_k_m.gguf"

PI_IP="10.10.10.2"
PI_API_PORT="8081"
PI_LLAMA_SERVER="/opt/llama.cpp/llama-server"
PI_LLAMA_CLI="/opt/llama.cpp/llama-cli"
PI_MODEL="/root/models/qwen2.5-3b-instruct-q4_k_m.gguf"

# ── Helper ───────────────────────────────────────────────────────────────────
run_on_laptop() { ssh -o ConnectTimeout=10 "root@${LAPTOP_IP}" "$@"; }
run_on_pi()     { ssh -o ConnectTimeout=10 "root@${PI_IP}" "$@"; }

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

usage() {
    cat <<EOF
Usage: $0 <command>

Commands:
  setup      Install ARM64 llama.cpp binaries on the Pi (one-time)
  start      Start RPC worker on laptop, then primary on Pi
  stop       Kill all llama-server processes on both machines
  test       Send a test prompt to the RPC cluster
  status     Show RPC processes and RAM on both machines
  load-test  Run a longer benchmark with token/s measurement
  teardown   Stop everything and restart normal services (Ollama on Pi)

Examples:
  $0 setup          # First-time: download + install ARM64 binaries on Pi
  $0 start          # Start the RPC cluster
  $0 test           # "Hello, what is 2+2?"
  $0 load-test      # Benchmark with timing
  $0 stop           # Kill RPC processes
  $0 teardown       # Stop RPC, restart Ollama, restore normal state
EOF
    exit 0
}

# ── setup ────────────────────────────────────────────────────────────────────
cmd_setup() {
    echo "=== 1. Download latest ARM64 release ==="
    run_on_laptop bash -c "
        cd /tmp
        TAG=\$(curl -sIL -o /dev/null -w '%{url_effective}' https://github.com/ggml-org/llama.cpp/releases/latest | sed -n 's|.*tag/\([^/?]*\).*|\1|p')
        echo \"Release tag: \$TAG\"
        curl -sLO --max-time 180 \"https://github.com/ggml-org/llama.cpp/releases/download/\${TAG}/llama-\${TAG}-bin-ubuntu-vulkan-arm64.tar.gz\"
        tar -xzf llama-*-bin-ubuntu-vulkan-arm64.tar.gz
        echo \"Extracted: \$(ls -d llama-*/)\"
    "

    echo ""
    echo "=== 2. Deploy to Pi ==="
    run_on_laptop bash -c "
        ssh root@${PI_IP} 'mkdir -p /opt/llama.cpp && rm -f /opt/llama.cpp/*'
        scp -r /tmp/llama-*/build/bin/* root@${PI_IP}:/opt/llama.cpp/ 2>/dev/null || \
        scp -r /tmp/llama-*/* root@${PI_IP}:/opt/llama.cpp/
        ssh root@${PI_IP} 'chmod +x /opt/llama.cpp/llama-server /opt/llama.cpp/llama-cli'
    "

    echo ""
    echo "=== 3. Verify Pi binary ==="
    run_on_pi "/opt/llama.cpp/llama-server --help 2>&1 | grep -i rpc | head -3"

    echo ""
    echo "✅ Setup complete. Next: $0 start"
}

# ── start ────────────────────────────────────────────────────────────────────
cmd_start() {
    echo "=== 1. Check model exists ==="
    run_on_laptop "ls -lh ${LAPTOP_MODEL}" || {
        echo "❌ Model missing on laptop. Copy it:"
        echo "   scp root@${PI_IP}:${PI_MODEL} root@${LAPTOP_IP}:${LAPTOP_MODEL}"
        exit 1
    }
    run_on_pi "ls -lh ${PI_MODEL}" || {
        echo "❌ Model missing on Pi."
        exit 1
    }

    echo ""
    echo "=== 2. Kill any stale processes ==="
    cmd_stop

    echo ""
    echo "=== 3. Free RAM on Pi (stop Ollama) ==="
    run_on_pi "systemctl stop ollama.service 2>/dev/null && echo '  Ollama stopped' || echo '  Ollama was already stopped'"
    sleep 2

    echo ""
    echo "=== 4. RAM before starting ==="
    echo "  Laptop:" && run_on_laptop "free -h | head -2 | tail -1"
    echo "  Pi:"     && run_on_pi     "free -h | head -2 | tail -1"

    echo ""
    echo "=== 5. Start RPC worker on laptop (port ${LAPTOP_RPC_PORT}) ==="
    run_on_laptop "
        nohup ${LAPTOP_LLAMA_SERVER} \
            -m ${LAPTOP_MODEL} \
            --host 0.0.0.0 \
            --port ${LAPTOP_RPC_PORT} \
            > /tmp/llama-rpc-worker.log 2>&1 &
        echo \"  Worker PID: \$!\"
    "
    # Wait up to 60s for worker to load the model (ARM/x86 can be slow)
    echo "  Waiting for worker to load model (may take 20-40s)..."
    for i in $(seq 1 12); do
        sleep 5
        if run_on_laptop "ss -tlnp | grep -q ${LAPTOP_RPC_PORT}" 2>/dev/null; then
            echo "  ✅ Worker listening on ${LAPTOP_RPC_PORT} (after ${i}x5s)"
            break
        fi
        if [ "$i" -eq 12 ]; then
            echo "  ❌ Worker failed to start after 60s. Log:"
            run_on_laptop "tail -20 /tmp/llama-rpc-worker.log"
            exit 1
        fi
    done

    echo ""
    echo "=== 6. Start PRIMARY on Pi (API on port ${PI_API_PORT}) ==="
    run_on_pi "
        nohup ${PI_LLAMA_SERVER} \
            -m ${PI_MODEL} \
            --rpc ${LAPTOP_IP}:${LAPTOP_RPC_PORT} \
            -ngl 99 \
            --host 0.0.0.0 \
            --port ${PI_API_PORT} \
            > /tmp/llama-rpc-primary.log 2>&1 &
        echo \"  Primary PID: \$!\"
    "
    # Wait up to 60s for primary to load and connect to worker
    echo "  Waiting for primary to load and connect to RPC worker..."
    for i in $(seq 1 12); do
        sleep 5
        if run_on_pi "ss -tlnp | grep -q ${PI_API_PORT}" 2>/dev/null; then
            echo "  ✅ Primary listening on ${PI_API_PORT} (after ${i}x5s)"
            break
        fi
        if [ "$i" -eq 12 ]; then
            echo "  ⚠️  Primary not listening after 60s. Check log:"
            run_on_pi "tail -10 /tmp/llama-rpc-primary.log"
            echo "  (If it shows 'Failed to connect', RPC handshake may have timed out)"
        fi
    done

    echo ""
    echo "  ✅ RPC cluster started. Test it: $0 test"
}

# ── stop ─────────────────────────────────────────────────────────────────────
cmd_stop() {
    echo "Stopping llama processes on both machines..."
    run_on_laptop "pkill -f llama-server 2>/dev/null; pkill -f llama-cli 2>/dev/null; echo '  Laptop: cleaned'"
    run_on_pi     "pkill -f llama-server 2>/dev/null; pkill -f llama-cli 2>/dev/null; echo '  Pi: cleaned'"
    sleep 1
}

# ── test ─────────────────────────────────────────────────────────────────────
cmd_test() {
    local prompt="${1:-Hello, what is 2+2?}"
    local tokens="${2:-32}"

    echo "Sending to Pi (${PI_IP}:${PI_API_PORT})..."
    echo "  Prompt: \"${prompt}\""
    echo "  Max tokens: ${tokens}"
    echo ""

    # Safely encode prompt as JSON to avoid injection from special characters
    SAFE_JSON=$(python3 -c "import json; print(json.dumps({
        'model': 'gpt-3.5-turbo',
        'messages': [{'role': 'user', 'content': '${prompt}'}],
        'max_tokens': ${tokens}
    }))")

    # Safely encode prompt as JSON to avoid injection from special characters
    SAFE_JSON=$(python3 -c "import json; print(json.dumps({
        'model': 'gpt-3.5-turbo',
        'messages': [{'role': 'user', 'content': '${prompt}'}],
        'max_tokens': ${tokens}
    }))")

    curl -s --max-time 60 \
        -X POST "http://${PI_IP}:${PI_API_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "${SAFE_JSON}" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {})
    print(f'Response: {content}')
    print(f'Tokens: prompt={usage.get(\"prompt_tokens\",\"?\")}, completion={usage.get(\"completion_tokens\",\"?\")}')
except Exception as e:
    print(f'Parse error: {e}')
    print('Raw:', sys.stdin.read() if hasattr(sys.stdin, 'read') else 'N/A')
" 2>&1 || echo "❌ Request failed — is the cluster running? ($0 start)"
}

# ── load-test ────────────────────────────────────────────────────────────────
cmd_load_test() {
    echo "=== RPC Load Test ==="
    echo ""

    local prompt="Explain the concept of distributed computing in one paragraph."
    local tokens=128

    echo "Prompt: ${prompt}"
    echo "Max tokens: ${tokens}"
    echo ""

    START_TIME=$(date +%s.%N)
    RESULT=$(curl -s --max-time 120 \
        -X POST "http://${PI_IP}:${PI_API_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"gpt-3.5-turbo\",
            \"messages\": [{\"role\": \"user\", \"content\": \"${prompt}\"}],
            \"max_tokens\": ${tokens},
            \"stream\": false
        }" 2>&1)
    END_TIME=$(date +%s.%N)

    # Do timing inside python3 (avoids bc dependency)
    echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {})
    prompt_tok = usage.get('prompt_tokens', 0)
    comp_tok = usage.get('completion_tokens', 0)
    elapsed = ${END_TIME} - ${START_TIME}
    tok_s = comp_tok / elapsed if elapsed > 0 else 0
    print(f'Response: {content[:500]}')
    print(f'')
    print(f'--- Stats ---')
    print(f'Total time:   {elapsed:.1f}s')
    print(f'Prompt tokens: {prompt_tok}')
    print(f'Output tokens: {comp_tok}')
    print(f'Throughput:    {tok_s:.1f} tok/s')
except Exception as e:
    print(f'Parse error: {e}')
"

    echo ""
    echo "=== RPC Worker Log (last 5 lines) ==="
    run_on_laptop "tail -5 /tmp/llama-rpc-worker.log 2>/dev/null || echo 'No log'"

    echo ""
    echo "=== Pi Primary Log (last 5 lines) ==="
    run_on_pi "tail -5 /tmp/llama-rpc-primary.log 2>/dev/null || echo 'No log'"
}

# ── status ───────────────────────────────────────────────────────────────────
cmd_status() {
    echo "=== LAPTOP (${LAPTOP_IP}) ==="
    echo "  RPC worker:"
    run_on_laptop "ss -tlnp | grep ${LAPTOP_RPC_PORT} || echo '    NOT RUNNING'"
    echo "  RAM:"
    run_on_laptop "free -h | head -2 | tail -1"
    echo "  Worker log tail:"
    run_on_laptop "tail -3 /tmp/llama-rpc-worker.log 2>/dev/null || echo '    No log'"

    echo ""
    echo "=== PI (${PI_IP}) ==="
    echo "  API server:"
    run_on_pi "ss -tlnp | grep ${PI_API_PORT} || echo '    NOT RUNNING'"
    echo "  RAM:"
    run_on_pi "free -h | head -2 | tail -1"
    echo "  Primary log tail:"
    run_on_pi "tail -3 /tmp/llama-rpc-primary.log 2>/dev/null || echo '    No log'"
}

# ── teardown ─────────────────────────────────────────────────────────────────
cmd_teardown() {
    echo "=== 1. Stop RPC processes ==="
    cmd_stop

    echo ""
    echo "=== 2. Restart Ollama on Pi ==="
    run_on_pi "systemctl start ollama.service && sleep 2 && systemctl is-active ollama.service && echo '  ✅ Ollama running' || echo '  ⚠️  Ollama failed to start'"

    echo ""
    echo "=== 3. Restart pi-classifier-server ==="
    run_on_pi "systemctl restart pi-classifier-server 2>/dev/null && echo '  ✅ Classifier running' || echo '  ⚠️  Classifier not installed'"

    echo ""
    echo "=== 4. Final state ==="
    echo "  Laptop RAM:" && run_on_laptop "free -h | head -2 | tail -1"
    echo "  Pi RAM:"     && run_on_pi     "free -h | head -2 | tail -1"
    echo ""
    echo "  ✅ Teardown complete. Normal services restored."
}

# ══════════════════════════════════════════════════════════════════════════════
#  DISPATCH
# ══════════════════════════════════════════════════════════════════════════════
case "${1:-usage}" in
    setup)      shift; cmd_setup "$@" ;;
    start)      shift; cmd_start "$@" ;;
    stop)       shift; cmd_stop "$@" ;;
    test)       shift; cmd_test "$@" ;;
    load-test)  shift; cmd_load_test "$@" ;;
    status)     shift; cmd_status "$@" ;;
    teardown)   shift; cmd_teardown "$@" ;;
    *)          usage ;;
esac

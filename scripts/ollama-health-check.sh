#!/bin/bash
# Ollama health check — called every 5 minutes by systemd timer.
# If Ollama's API is not responding, restart the service.
#
# Logs: journalctl -u ollama-health.service
#
set -euo pipefail

API_URL="http://localhost:11434/api/tags"
MAX_WAIT=10  # seconds to wait for Ollama to become healthy

# ── Check if service was explicitly stopped (maintenance mode) ─────────────────
UNIT_STATE=$(systemctl is-active ollama.service 2>/dev/null || echo "unknown")
if [ "$UNIT_STATE" = "inactive" ]; then
    # Service was deliberately stopped — don't auto-restart
    echo "$(date -Iseconds) ollama.service is inactive (maintenance?). Not restarting."
    exit 0
fi

# ── Check if Ollama API is responding ─────────────────────────────────────────
if curl -sf --max-time 5 "$API_URL" > /dev/null 2>&1; then
    # Ollama is healthy — nothing to do
    exit 0
fi

# ── Ollama is not responding — restart it ─────────────────────────────────────
echo "$(date -Iseconds) Ollama health check FAILED — restarting service..."

systemctl restart ollama.service

# Wait for it to come back
for i in $(seq 1 $MAX_WAIT); do
    sleep 1
    if curl -sf --max-time 3 "$API_URL" > /dev/null 2>&1; then
        echo "$(date -Iseconds) Ollama restarted and healthy after ${i}s"
        exit 0
    fi
done

echo "$(date -Iseconds) WARNING: Ollama did not become healthy within ${MAX_WAIT}s after restart"
exit 1

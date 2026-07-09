#!/bin/bash
# Bot Health Monitor — runs every 4 hours via systemd timer.
# Sends a dynamic health report to Telegram.
#
# Logs: journalctl -u bot-health.service
#
set -euo pipefail

BOT_DIR="/home/sanel/personal-assistant-bot"
TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN "$BOT_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d '"')
CHAT_ID="8534649457"

# ── Gather health data ────────────────────────────────────────────────────────

# Bot service
BOT_ACTIVE=$(systemctl is-active bot.service 2>/dev/null || echo "unknown")
BOT_UPTIME=$(systemctl show bot.service -p ActiveEnterTimestamp 2>/dev/null | cut -d= -f2 || echo "?")
BOT_PID=$(systemctl show bot.service -p MainPID 2>/dev/null | cut -d= -f2 || echo "?")

# Ollama
OLLAMA_ACTIVE=$(systemctl is-active ollama.service 2>/dev/null || echo "unknown")
OLLAMA_MODELS=$(curl -sf --max-time 3 http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('models',[])))" 2>/dev/null || echo "?")

# Disk
DISK_PCT=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
DISK_FREE=$(df -h / | tail -1 | awk '{print $4}')

# Recent errors (last 4 hours)
ERROR_COUNT=$(journalctl -u bot.service --no-pager --since "4 hours ago" 2>/dev/null | grep -ciE "error|fail|traceback" || echo "0")

# File sizes
STATE_KB=$(du -k "$BOT_DIR/state.json" 2>/dev/null | cut -f1 || echo "0")
SUMMARIES_KB=$(du -k "$BOT_DIR/source_cache/combined_summaries.txt" 2>/dev/null | cut -f1 || echo "0")
BRAIN_KB=$(du -k "$BOT_DIR/curated_brain.md" 2>/dev/null | cut -f1 || echo "0")
INDEX_KB=$(du -k "$BOT_DIR/mega_index.md" 2>/dev/null | cut -f1 || echo "0")

# Nightly queue
QUEUE_SIZE=$(python3 -c "import json; print(len(json.load(open('$BOT_DIR/nightly_queue.json'))))" 2>/dev/null || echo "0")

# Last digest
LAST_DIGEST="never"
if [ -f "$BOT_DIR/latest_digest.txt" ]; then
    LAST_DIGEST=$(stat -c %y "$BOT_DIR/latest_digest.txt" 2>/dev/null | cut -d. -f1 || echo "unknown")
fi

# Google scrapers
GOOGLE_TOKEN=$(python3 -c "
import json, os, sys
sys.path.insert(0, '$BOT_DIR')
os.chdir('$BOT_DIR')
try:
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file('token.json', [])
    print('valid' if creds.valid else 'expired')
except:
    print('missing')
" 2>/dev/null || echo "error")

# ── Build report ──────────────────────────────────────────────────────────────

BOT_STATUS_EMOJI="✅"
OLLAMA_STATUS_EMOJI="⚠️"
if [ "$BOT_ACTIVE" != "active" ]; then BOT_STATUS_EMOJI="🚨"; fi
if [ "$OLLAMA_ACTIVE" = "active" ]; then OLLAMA_STATUS_EMOJI="✅"; fi

REPORT=$(cat << ENDREPORT
🤖 **Bot Health Check** — $(date '+%Y-%m-%d %H:%M %Z')

**Services:**
• Telegram bot: $BOT_STATUS_EMOJI $BOT_ACTIVE (since $(echo $BOT_UPTIME | cut -d' ' -f2-3))
• Ollama: $OLLAMA_STATUS_EMOJI $OLLAMA_ACTIVE ($OLLAMA_MODELS models loaded)

**System:**
• Disk: ${DISK_PCT}% used (${DISK_FREE} free)
• Google token: $GOOGLE_TOKEN
• Recent errors (4h): $ERROR_COUNT

**Data:**
• State: ${STATE_KB}KB
• Summaries: ${SUMMARIES_KB}KB
• Curated brain: ${BRAIN_KB}KB
• Mega index: ${INDEX_KB}KB
• Nightly queue: $QUEUE_SIZE files
• Last digest: $LAST_DIGEST

$([ "$ERROR_COUNT" -gt 0 ] && echo "⚠️ $ERROR_COUNT errors in last 4 hours — check journalctl -u bot.service")
$([ "$GOOGLE_TOKEN" = "expired" ] && echo "⚠️ Google token expired — run google_auth_setup.py")
$([ "$GOOGLE_TOKEN" = "missing" ] && echo "🚨 No token.json found!")
$([ "$OLLAMA_ACTIVE" != "active" ] && echo "⚠️ Ollama is not running — nightly pipeline will fail")
$([ "$BOT_ACTIVE" != "active" ] && echo "🚨 Bot is DOWN — check systemctl status bot.service")
ENDREPORT
)

# ── Send to Telegram ──────────────────────────────────────────────────────────

curl -sf --max-time 10 -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=${REPORT}" \
  -d "parse_mode=Markdown" \
  > /dev/null 2>&1 && echo "$(date -Iseconds) Health report sent OK" || echo "$(date -Iseconds) Failed to send health report"

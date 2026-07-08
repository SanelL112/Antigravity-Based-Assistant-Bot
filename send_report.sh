#!/bin/bash
TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN /home/sanel/personal-assistant-bot/.env | cut -d= -f2)
REPORT="🤖 Bot Health Check — 2026-07-06 08:04 ET

Service Status:
• Telegram bot: ✅ running (active since 06:21 AM EDT)
• Ollama: ⚠️ stopped (inactive)

Recent Issues (last 4h):
• Google scope warnings: 1 (classroom.coursework.me.readonly)
• Crashes: 1 CRITICAL — bot failed to start at 06:21:27 due to \`logger.Warning\` typo in llm_router.py:531 (should be \`logger.warning\`)
• Nightly log errors: 0 (last run Jul 3 successful)

Disk: 47% used (53G free of 104G)

Nightly Study Guides: 7.8M (6 guides, 3 core + 3 dynamic)

⚠️ Issues Found:
1. **Ollama inactive** — nightly pipeline needs it for local LLM. Fix: \`systemctl start ollama\`
2. **CRITICAL crash on startup** — llm_router.py line 531 has \`logger.Warning\` (capital W) which doesn't exist. Fix: \`sed -i 's/logger\.Warning/logger.warning/g' /home/sanel/personal-assistant-bot/llm_router.py\`
3. **Morning digest not delivered today** — latest_digest.txt is from Jun 29 (over a week ago). The morning_digest.py script is not scheduled (no systemd timer/cron found). If you want 7 AM digests, add a systemd timer or cron entry.
4. **Google Classroom scope warning** — missing \`classroom.coursework.me.readonly\`. Re-auth with broader scopes if needed.

✅ Nightly pipeline (Jul 3): Successful — 6 study guides created/updated, git push OK."

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
  -d "chat_id=8534649457" \
  -d "text=${REPORT}" \
  -d "parse_mode=Markdown"
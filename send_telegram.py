import os
import re
import urllib.request
import urllib.parse

if __name__ == "__main__":
    # Read the .env file
    with open('/home/sanel/personal-assistant-bot/.env', 'rb') as f:
        content = f.read()

    # Extract the token
    token = None
    for line in content.split(b'\n'):
        if line.startswith(b'TELEGRAM_BOT_TOKEN='):
            token = line.split(b'=', 1)[1].decode('utf-8')
            break

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)

    chat_id = "8534649457"

    message = """🤖 **Bot Health Report — 2026-07-12 04:00 EDT**

    ✅ **All clear**

    • **Services**: bot.service ✅ active, ollama ✅ active
    • **Google scope warnings**: 0 in last 4h (ResourceWarnings only — benign SSL socket warnings)
    • **Crashes**: 0 in last 24h
    • **Disk**: 70% used (69/104 GB)
    • **Nightly Study Guides**: 12 MB updated 2026-07-12 02:15 — 7 guides (467 KB master SAT + 3 core + 3 dynamic geometry)
    • **Nightly cron**: Completed successfully 02:15 EDT — updated 3 core SAT guides + created 3 new dynamic topic guides (Area/Volume, Central Idea, Advanced Triangles/Quadratics)
    • **Nightly log errors**: 0

    ✅ **All clear** — bot healthy, nightly guides updated, no errors."""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data)
    response = urllib.request.urlopen(req)
    result = response.read().decode('utf-8')
    print(result)
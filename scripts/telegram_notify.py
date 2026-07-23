#!/usr/bin/env python3
"""Telegram notification script for cron jobs.

Loads TELEGRAM_BOT_TOKEN from .env using python-dotenv to avoid shell token masking issues.

Usage:
  python3 telegram_notify.py "your message here"
  python3 telegram_notify.py --health-check   # Runs full bot health check and sends report
"""
import os
import sys
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/home/sanel/personal-assistant-bot/.env')

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = '8534649457'


def send_message(text: str, parse_mode: str = None) -> dict:
    """Send a message via Telegram Bot API."""
    if not TOKEN:
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN not loaded from .env'}

    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def send_plain_message(text: str) -> dict:
    """Send a plain text message (no markdown parsing) - reliable for structured reports."""
    return send_message(text, parse_mode=None)


def run_cmd(cmd: str) -> tuple[str, int]:
    """Run a shell command and return (stdout, exit_code)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.returncode


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    # Characters that MUST be escaped in MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def run_health_check() -> str:
    """Run the full bot health check and return formatted report."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M %Z')

    # CHECK 1: Bot Service Status
    bot_status, _ = run_cmd('systemctl is-active bot.service')
    bot_running = bot_status == 'active'

    # CHECK 2: Ollama Status
    ollama_status, _ = run_cmd('systemctl is-active ollama')
    ollama_running = ollama_status == 'active'

    # CHECK 3: Disk Space
    df_out, _ = run_cmd("df -h / | awk 'NR==2 {print $5}'")
    disk_pct = int(df_out.replace('%', '')) if df_out else 0

    # CHECK 4: Study Guides Size
    du_out, _ = run_cmd('du -sh /home/sanel/personal-assistant-bot/study_guides/')
    study_size = du_out.split('\t')[0] if du_out else 'unknown'

    # CHECK 5: Google Scope Warnings (last 4h)
    scope_count, _ = run_cmd('journalctl -u bot.service --since "4 hours ago" 2>/dev/null | grep -c "Not all requested scopes"')
    scope_count = int(scope_count) if scope_count else 0

    # CHECK 6: Crashes (last 4h)
    crash_out, _ = run_cmd(r'journalctl -u bot.service --since "4 hours ago" 2>/dev/null | grep -i "crash\|traceback\|fatal\|segfault"')
    crash_count = len(crash_out.strip().split('\n')) if crash_out.strip() else 0

    # CHECK 7: Nightly Log Errors (last 50 lines)
    nightly_out, _ = run_cmd('tail -50 /home/sanel/personal-assistant-bot/nightly.log 2>/dev/null')
    nightly_errors = 0
    if 'ERROR' in nightly_out or 'FAILED' in nightly_out.upper():
        nightly_errors = 1  # flag if any errors found

    # CHECK 8: Morning Digest (last 12h) + specific 7 AM check
    digest_out, _ = run_cmd('journalctl -u bot.service --since "12 hours ago" 2>/dev/null | grep -i "digest"')
    digest_sent = bool(digest_out.strip())

    # CHECK 8b: Specific 7 AM today check
    today_7am_out, _ = run_cmd(r'journalctl -u bot.service --since "today 07:00" --until "today 07:10" 2>/dev/null | grep -i "digest\|morning\|send_morning"')
    digest_7am_fired = bool(today_7am_out.strip())

    # Build report - use plain text to avoid MarkdownV2 escaping issues
    status_bot = 'running' if bot_running else 'stopped'
    status_ollama = 'running' if ollama_running else 'stopped (warning)'
    status_disk = f'{disk_pct}% used' + (' (warning)' if disk_pct > 85 else '')

    report = f"Bot Health Check - {now}\n\n"
    report += f"Service Status:\n"
    report += f"- Telegram bot: {status_bot}\n"
    report += f"- Ollama: {status_ollama}\n\n"

    report += f"Recent Issues (last 4h):\n"
    report += f"- Google scope warnings: {scope_count}\n"
    report += f"- Crashes: {crash_count}\n"
    report += f"- Nightly log errors: {nightly_errors}\n\n"

    report += f"Disk: {status_disk}\n\n"
    report += f"Nightly Study Guides: {study_size}\n\n"

    issues = []
    if not ollama_running:
        issues.append("Ollama service inactive - nightly pipeline needs it. Fix: sudo systemctl start ollama")
    if scope_count > 5:
        issues.append(f"High Google scope warnings ({scope_count}) - monitor auth")
    if disk_pct > 85:
        issues.append(f"Disk at {disk_pct}% - cleanup needed")
    if crash_count > 0:
        issues.append(f"{crash_count} crash(es) detected - check journalctl")
    if nightly_errors:
        issues.append("Nightly log has errors - check nightly.log")
    if not digest_7am_fired:
        issues.append("Morning digest did NOT fire at 7:00 AM today - check JobQueue scheduling")

    if issues:
        report += "Issues found:\n"
        for issue in issues:
            report += f"- {issue}\n"
    else:
        report += "All clear - bot healthy, no crashes, nightly pipeline clean, disk OK, digest sent"

    return report


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 telegram_notify.py "your message here"')
        print('       python3 telegram_notify.py --health-check')
        sys.exit(1)

    if sys.argv[1] == '--health-check':
        message = run_health_check()
    else:
        message = ' '.join(sys.argv[1:])

    result = send_plain_message(message)
    print(result)
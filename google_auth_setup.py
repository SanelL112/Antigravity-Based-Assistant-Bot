#!/usr/bin/env python3
"""
Standalone Google OAuth token generator for the personal assistant bot.

Run this on any computer with a browser.  It will copy the generated token.json
to the server (100.68.88.100) via SCP.

Usage:
    python3 google_auth_setup.py              # re-auth only if token expires soon
    python3 google_auth_setup.py --force      # force re-auth regardless

Designed to be called weekly by a launchd job – pops up a browser when the
refresh token is about to expire (Google testing-app refresh tokens last ~7 days).
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── Config ─────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

SCRIPT_DIR = Path(__file__).parent.resolve()
CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"
TOKEN_OUTPUT = SCRIPT_DIR / "token.json"
LOG_FILE = SCRIPT_DIR / "logs" / "google_token_refresh.log"

# Remote server where the bot runs
REMOTE_USER = "root"
REMOTE_HOST = "100.68.88.100"
REMOTE_TOKEN_PATH = "/home/sanel/personal-assistant-bot/token.json"
REMOTE_SERVICE = "bot.service"

# Re-auth if token expires within this many days
MIN_VALID_DAYS = 3


# ── Helpers ────────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    """Timestamped print + append to log file."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def token_is_fresh() -> bool:
    """Return True if token.json exists and is valid for at least MIN_VALID_DAYS."""
    if not TOKEN_OUTPUT.exists():
        log("No local token.json found — re-auth needed.")
        return False

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(TOKEN_OUTPUT), SCOPES)
    except Exception as e:
        log(f"Could not read token.json: {e} — re-auth needed.")
        return False

    if not creds or not creds.valid:
        log("Local token is invalid/expired — re-auth needed.")
        return False

    if creds.expiry:
        expiry = creds.expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        remaining = expiry - datetime.now(timezone.utc)
        days_left = remaining.total_seconds() / 86400
        if days_left < MIN_VALID_DAYS:
            log(f"Token expires in {days_left:.1f} days (< {MIN_VALID_DAYS}) — re-auth needed.")
            return False
        log(f"Token valid for {days_left:.1f} more days — skipping re-auth.")
        return True

    # No expiry info — assume it's fine
    log("Token has no expiry field — assuming fresh, skipping.")
    return True


def copy_to_server() -> bool:
    """SCP token.json to the remote server and restart the bot service."""
    log(f"Copying token.json to {REMOTE_HOST}...")

    try:
        result = subprocess.run(
            [
                "scp",
                "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=no",
                str(TOKEN_OUTPUT),
                f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_TOKEN_PATH}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            log(f"SCP failed: {result.stderr.strip()}")
            return False

        log("Token copied. Restarting bot service...")
        result = subprocess.run(
            [
                "ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                f"{REMOTE_USER}@{REMOTE_HOST}",
                f"systemctl restart {REMOTE_SERVICE}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            log(f"Service restart failed: {result.stderr.strip()}")
            return False

        log("Bot service restarted successfully.")
        return True
    except Exception as e:
        log(f"Copy to server failed: {e}")
        return False


def do_auth() -> bool:
    """Run the browser-based OAuth flow. Returns True on success."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        log("ERROR: google-auth-oauthlib not installed. Run: pip3 install google-auth-oauthlib")
        return False

    if not CREDENTIALS_PATH.exists():
        log(f"ERROR: credentials.json not found at {CREDENTIALS_PATH}")
        return False

    log("Opening browser for Google OAuth...")
    print("Scopes being requested:")
    for scope in SCOPES:
        print(f"  - {scope}")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)

    try:
        creds = flow.run_local_server(
            host="127.0.0.1",
            port=8080,
            prompt="consent",
            open_browser=True,
            success_message="Authentication successful! You can close this tab.",
        )
    except Exception as e:
        log(f"Browser OAuth failed: {e}")
        return False

    with open(TOKEN_OUTPUT, "w") as f:
        f.write(creds.to_json())

    log(f"Token saved locally: {TOKEN_OUTPUT}")
    log(f"Token expires: {creds.expiry}")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Google OAuth token for the bot.")
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-authentication even if the current token is still fresh.",
    )
    args = parser.parse_args()

    # ── Smart skip: if token is fresh, do nothing ──────────────────────────
    if not args.force and token_is_fresh():
        log("Token is fresh — nothing to do. (Use --force to re-auth anyway.)")
        return 0

    # ── Run browser-based OAuth ────────────────────────────────────────────
    log("Starting Google OAuth re-authentication...")
    if not do_auth():
        log("OAuth failed — token was NOT refreshed.")
        return 1

    # ── Copy to server ─────────────────────────────────────────────────────
    if copy_to_server():
        log("Done! Token refreshed and deployed to server.")
    else:
        log("WARNING: Token generated locally but could NOT copy to server.")
        log(f"  Manually SCP {TOKEN_OUTPUT} to {REMOTE_HOST}:{REMOTE_TOKEN_PATH}")
        log(f"  Then run: ssh {REMOTE_HOST} systemctl restart {REMOTE_SERVICE}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Standalone Google OAuth token generator for the personal assistant bot.
Run this on any computer with a browser. Copy the generated token.json to the server.

Usage:
    python3 google_auth_setup.py

Requirements:
    pip install google-auth google-auth-oauthlib

The script will:
    1. Load credentials.json from the same directory
    2. Open your browser for Google OAuth
    3. Save token.json in the same directory
    4. Copy token.json to ~/personal-assistant-bot/token.json on the server
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Google API scopes needed by the bot
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

SCRIPT_DIR = Path(__file__).parent.resolve()
CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"
TOKEN_OUTPUT = SCRIPT_DIR / "token.json"

def main():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: Install required packages first:")
        print("  pip install google-auth google-auth-oauthlib")
        sys.exit(1)

    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: credentials.json not found at {CREDENTIALS_PATH}")
        print("Download it from Google Cloud Console -> APIs & Services -> Credentials")
        sys.exit(1)

    print("=" * 60)
    print("Google OAuth Setup for Personal Assistant Bot")
    print("=" * 60)
    print()
    print("This will open your browser to authorize the bot.")
    print("Scopes being requested:")
    for scope in SCOPES:
        print(f"  - {scope}")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        SCOPES
    )

    # Try local server first (works on desktop with browser)
    # Fall back to console flow (works on headless/remote)
    try:
        creds = flow.run_local_server(
            host='127.0.0.1',
            port=8080,
            prompt='consent',
            open_browser=True,
            success_message="Authentication successful! You can close this tab."
        )
    except Exception as e:
        print(f"Local server failed ({e}), you may need to run this on a computer with a browser.")
        sys.exit(1)

    # Save token
    with open(TOKEN_OUTPUT, 'w') as f:
        f.write(creds.to_json())

    print()
    print(f"Token saved to: {TOKEN_OUTPUT}")
    print(f"Token expiry: {creds.expiry}")
    print()

    # Try to copy to server if reachable
    server_token = Path.home() / "personal-assistant-bot" / "token.json"
    if server_token.parent.exists():
        shutil.copy2(TOKEN_OUTPUT, server_token)
        print(f"Token copied to server: {server_token}")
        print("Done! The bot can now use Google APIs.")
    else:
        print(f"Server path not found: {server_token}")
        print(f"Copy {TOKEN_OUTPUT} to ~/personal-assistant-bot/token.json on the server.")
        print()
        print("Then restart the bot: systemctl restart bot.service")

if __name__ == "__main__":
    main()

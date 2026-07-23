"""Shared test configuration that keeps the suite independent of a local .env."""

import os


_TEST_ENV = {
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "TELEGRAM_BOT_TOKEN": "test-telegram-token",
    "TELEGRAM_CHAT_ID": "1",
    "CONVERSATION_ID": "test-conversation",
}

for _name, _value in _TEST_ENV.items():
    os.environ.setdefault(_name, _value)

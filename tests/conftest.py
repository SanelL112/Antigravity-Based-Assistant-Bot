import pytest
import os
import sys

# We need to set env vars before config.py is imported
os.environ["OPENROUTER_API_KEY"] = "dummy"
os.environ["TELEGRAM_BOT_TOKEN"] = "dummy"
os.environ["TELEGRAM_CHAT_ID"] = "123"
os.environ["CONVERSATION_ID"] = "456"

# We must prevent config.py from creating paths that might not exist or need permissions, like /mnt/orangepi.
# Since config.py is executed as soon as it's imported, we can mock `pathlib.Path.mkdir` safely before we import `config`.
from unittest.mock import patch
import pathlib

# We use a patch on pathlib.Path.mkdir to suppress permission/not-found errors during import config
# But we only apply it during import so it doesn't leak into tests globally
original_mkdir = pathlib.Path.mkdir

def safe_mkdir(self, mode=0o777, parents=False, exist_ok=False):
    try:
        original_mkdir(self, mode, parents, exist_ok)
    except Exception:
        pass

# We apply this temporarily during initial test discovery
with patch('pathlib.Path.mkdir', new=safe_mkdir):
    # This will trigger config.py and allow it to initialize without raising errors
    import config
    import bot.state

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("CONVERSATION_ID", "456")

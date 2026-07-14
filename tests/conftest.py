import os
from unittest.mock import patch
import builtins

# Set dummy environment variables to avoid validation errors in config.py
# This runs before imports in test modules.
os.environ["OPENROUTER_API_KEY"] = "dummy_key"
os.environ["TELEGRAM_BOT_TOKEN"] = "dummy_token"
os.environ["TELEGRAM_CHAT_ID"] = "123456789"
os.environ["CONVERSATION_ID"] = "dummy_conv"
os.environ["NOTION_API_KEY"] = "dummy_notion_key"

# Patch pathlib.Path.mkdir at import time since config.py calls it globally
import pathlib
original_mkdir = pathlib.Path.mkdir
def mock_mkdir_import_safe(self, mode=0o777, parents=False, exist_ok=False):
    if "/mnt/orangepi" in str(self) or "cache" in str(self):
        return
    original_mkdir(self, mode, parents, exist_ok)
pathlib.Path.mkdir = mock_mkdir_import_safe

import pytest

@pytest.fixture(autouse=True)
def mock_mkdir():
    with patch("pathlib.Path.mkdir") as mock:
        yield mock

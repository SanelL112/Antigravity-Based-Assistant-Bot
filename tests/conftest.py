import os
import pytest
import pathlib

# Before importing config, we need to set the env variables or patch them
os.environ["OPENROUTER_API_KEY"] = "dummy"
os.environ["TELEGRAM_BOT_TOKEN"] = "dummy"
os.environ["TELEGRAM_CHAT_ID"] = "123"
os.environ["CONVERSATION_ID"] = "dummy"
os.environ["NOTION_API_KEY"] = "dummy"

original_mkdir = pathlib.Path.mkdir

def dummy_mkdir(self, *args, **kwargs):
    try:
        original_mkdir(self, *args, **kwargs)
    except Exception:
        # Ignore permission errors for /mnt/orangepi etc
        pass

pathlib.Path.mkdir = dummy_mkdir

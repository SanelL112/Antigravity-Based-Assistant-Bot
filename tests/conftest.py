"""Shared test configuration that keeps the suite independent of a local .env."""

import os


_TEST_ENV = {
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "TELEGRAM_BOT_TOKEN": "test-telegram-token",
    "TELEGRAM_CHAT_ID": "1",
    "CONVERSATION_ID": "test-conversation",
}

for _name, _value in _TEST_ENV.items():
    os.environ[_name] = _value  # OVERRIDE any real credentials from environment

import pytest
import socket

@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch):
    """
    Block all network requests in tests by default.
    Tests that need network should explicitly mock the required modules.
    """
    def block_network(*args, **kwargs):
        raise RuntimeError("Network calls are disabled in tests!")
    
    # Block socket level
    monkeypatch.setattr(socket, "socket", block_network)
    
    # Block requests/httpx if they try to bypass or are already imported
    try:
        import requests
        monkeypatch.setattr(requests, "get", block_network)
        monkeypatch.setattr(requests, "post", block_network)
        monkeypatch.setattr(requests.Session, "request", block_network)
    except ImportError:
        pass
        
    try:
        import httpx
        monkeypatch.setattr(httpx, "get", block_network)
        monkeypatch.setattr(httpx, "post", block_network)
        monkeypatch.setattr(httpx.Client, "request", block_network)
        monkeypatch.setattr(httpx.AsyncClient, "request", block_network)
    except ImportError:
        pass


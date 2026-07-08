import sys
import unittest.mock

# Mock config to avoid side effects (like creating /mnt dirs or env validation) during testing
mock_config = unittest.mock.MagicMock()
mock_config.STATE_FILE = "dummy_state.json"
sys.modules['config'] = mock_config

import pytest
import hashlib
from bot.state import get_hash

def test_get_hash_standard_string():
    """Test get_hash with a standard alphanumeric string."""
    text = "hello world"
    expected = hashlib.md5(text.encode('utf-8')).hexdigest()
    assert get_hash(text) == expected
    assert get_hash(text) == '5eb63bbbe01eeed093cb22bb8f5acdc3'

def test_get_hash_empty_string():
    """Test get_hash with an empty string."""
    text = ""
    expected = hashlib.md5(text.encode('utf-8')).hexdigest()
    assert get_hash(text) == expected
    assert get_hash(text) == 'd41d8cd98f00b204e9800998ecf8427e'

def test_get_hash_special_characters():
    """Test get_hash with special characters and emojis to test utf-8 encoding."""
    text = "hello 🌍 and 🚀! 123"
    expected = hashlib.md5(text.encode('utf-8')).hexdigest()
    assert get_hash(text) == expected

def test_get_hash_deterministic():
    """Test that get_hash is deterministic (same input produces same output)."""
    text = "consistent output"
    assert get_hash(text) == get_hash(text)

def test_get_hash_different_inputs():
    """Test that different inputs produce different hashes."""
    text1 = "apple"
    text2 = "orange"
    assert get_hash(text1) != get_hash(text2)

def test_get_hash_type_error():
    """Test get_hash handles non-string inputs properly (should raise AttributeError on .encode)."""
    with pytest.raises(AttributeError):
        get_hash(123)
    with pytest.raises(AttributeError):
        get_hash(None)

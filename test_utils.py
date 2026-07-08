import pytest
from utils import scrub_pii

def test_scrub_pii_empty_string():
    """Test that empty string or None are handled correctly."""
    assert scrub_pii("") == ""
    assert scrub_pii(None) is None

def test_scrub_pii_no_pii():
    """Test that text without PII remains unchanged."""
    text = "The quick brown fox jumps over the lazy dog."
    assert scrub_pii(text) == text
    assert scrub_pii(text, aggressive=True) == text

def test_scrub_pii_basic():
    """Test standard PII removal without aggressive scrubbing."""
    text = (
        "Email: test@example.com, "
        "Phone: 555-123-4567, "
        "SSN: 123-45-6789, "
        "Card: 1234-5678-9012-3456, "
        "DOB: 01/01/2000, "
        "Student ID: 123456, "
        "IP: 192.168.1.1, "
        "Path: /home/user/docs"
    )
    scrubbed = scrub_pii(text)

    assert "[EMAIL]" in scrubbed
    assert "[PHONE]" in scrubbed
    assert "[SSN]" in scrubbed
    assert "[CARD]" in scrubbed
    assert "[DATE]" in scrubbed
    assert "[ID]" in scrubbed
    assert "[IP_ADDRESS]" in scrubbed
    assert "[HOME_DIR]" in scrubbed

    assert "test@example.com" not in scrubbed
    assert "555-123-4567" not in scrubbed
    assert "123-45-6789" not in scrubbed
    assert "1234-5678-9012-3456" not in scrubbed
    assert "01/01/2000" not in scrubbed
    assert "123456" not in scrubbed
    assert "192.168.1.1" not in scrubbed
    assert "/home/user" not in scrubbed

def test_scrub_pii_aggressive():
    """Test that aggressive mode removes capitalized names."""
    text = "Hello John Doe, please check the system."

    # Non-aggressive keeps the name
    assert "John Doe" in scrub_pii(text, aggressive=False)

    # Aggressive removes the name
    aggressive_scrubbed = scrub_pii(text, aggressive=True)
    assert "John Doe" not in aggressive_scrubbed
    assert "[NAME]" in aggressive_scrubbed

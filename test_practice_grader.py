import pytest
from practice_grader import _safe_parse_json

def test_safe_parse_json_direct():
    """Test parsing a valid JSON string directly."""
    text = '[{"problem": 1, "user_answer": "A"}]'
    result = _safe_parse_json(text)
    assert result == [{"problem": 1, "user_answer": "A"}]

def test_safe_parse_json_embedded():
    """Test extracting and parsing JSON embedded within extra text."""
    text = '''Here is the extracted data:
```json
[
  {"problem": 1, "user_answer": "B"},
  {"problem": 2, "user_answer": "C"}
]
```
Let me know if you need anything else.'''
    result = _safe_parse_json(text)
    assert result == [
        {"problem": 1, "user_answer": "B"},
        {"problem": 2, "user_answer": "C"}
    ]

def test_safe_parse_json_empty_list():
    """Test parsing an empty JSON list, both directly and embedded."""
    assert _safe_parse_json("[]") == []
    assert _safe_parse_json("Some text [] more text") == []

def test_safe_parse_json_no_json():
    """Test behavior when no JSON array is present in the text."""
    text = "There is no json here."
    assert _safe_parse_json(text) is None

def test_safe_parse_json_malformed_json():
    """Test behavior with malformed JSON inside brackets."""
    text = 'Here is some data: [{"problem": 1, missing_quotes: "B"}]'
    assert _safe_parse_json(text) is None

def test_safe_parse_json_dict_instead_of_list():
    """Test behavior if a JSON object is provided instead of a list.

    _safe_parse_json expects an Optional[list], but json.loads can return a dict.
    The current implementation returns the parsed dict.
    We should ensure it handles it without crashing.
    """
    text = '{"problem": 1, "user_answer": "A"}'
    result = _safe_parse_json(text)
    assert result == {"problem": 1, "user_answer": "A"}

def test_safe_parse_json_embedded_malformed_array_but_valid_later():
    """Test behavior with multiple bracket pairs where first might be invalid JSON."""
    text = '''Some text with brackets [not json].
Then valid json:
[{"problem": 1, "user_answer": "A"}]
'''
    # The current regex r'\[[\s\S]*?\]' finds the first occurrence of brackets.
    # It finds `[not json]`, fails to parse it, and returns None.
    # We document the current behavior in the test.
    assert _safe_parse_json(text) is None

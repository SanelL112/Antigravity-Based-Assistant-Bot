import pytest
from llm_router import is_valid_response

def test_is_valid_response_empty_or_short():
    assert not is_valid_response("")
    assert not is_valid_response("   ")
    assert not is_valid_response("a" * 4)
    # The heuristic checking currently fails for falsy value.
    assert not is_valid_response(None)

def test_is_valid_response_system_prompt_regurgitation():
    assert not is_valid_response("You are a powerful personal assistant, I'm here to help.")
    assert not is_valid_response("You are Sanel, how can I assist you?")
    assert is_valid_response("You are a great helper.") # Valid start

def test_is_valid_response_short_refusals():
    # Should be invalid
    assert not is_valid_response("I cannot do that.")
    assert not is_valid_response("I'm sorry, I cannot assist with this.")
    assert not is_valid_response("As an AI, I don't know the answer.")
    assert not is_valid_response("Unable to comply with your request.")
    assert not is_valid_response("I apologize for the inconvenience.")

    # It checks the first 50 characters, and total length < 100
    assert not is_valid_response("Well, I'm sorry to say this, but I can't help.")

    # Valid: longer than 100 characters, even with fail phrases
    long_refusal = "I'm sorry, but I really cannot do that. " * 5
    assert is_valid_response(long_refusal)

    # Valid: less than 100 chars, no fail phrases
    assert is_valid_response("This is a valid response that is short but acceptable.")

def test_is_valid_response_valid():
    assert is_valid_response("This is a valid response that provides useful information.")
    assert is_valid_response("Hello! How can I help you today?")
    assert is_valid_response("Here is the answer to your question: 42.")
    assert is_valid_response("The capital of France is Paris.")

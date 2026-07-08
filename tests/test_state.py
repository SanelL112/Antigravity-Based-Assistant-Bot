import os
import json
import pytest
from bot.state import load_state

def test_load_state_no_file(monkeypatch, tmp_path):
    # Set STATE_FILE to a non-existent path
    test_state_file = tmp_path / "non_existent.json"
    monkeypatch.setattr("bot.state.STATE_FILE", test_state_file)

    state = load_state()

    assert state == {
        "seen_tasks": [],
        "seen_alerts": [],
        "pending_priorities": {},
        "user_models": {}
    }

def test_load_state_with_all_keys(monkeypatch, tmp_path):
    test_state_file = tmp_path / "state.json"
    data = {
        "seen_tasks": ["task1"],
        "seen_alerts": ["alert1"],
        "pending_priorities": {"user1": "high"},
        "user_models": {"user1": "modelA"}
    }
    with open(test_state_file, "w") as f:
        json.dump(data, f)

    monkeypatch.setattr("bot.state.STATE_FILE", test_state_file)

    state = load_state()

    assert state == data

def test_load_state_missing_some_keys(monkeypatch, tmp_path):
    test_state_file = tmp_path / "state.json"
    data = {
        "seen_tasks": ["task1"],
        "seen_alerts": ["alert1"]
        # Missing pending_priorities and user_models
    }
    with open(test_state_file, "w") as f:
        json.dump(data, f)

    monkeypatch.setattr("bot.state.STATE_FILE", test_state_file)

    state = load_state()

    assert state["seen_tasks"] == ["task1"]
    assert state["seen_alerts"] == ["alert1"]
    assert state["pending_priorities"] == {}
    assert state["user_models"] == {}

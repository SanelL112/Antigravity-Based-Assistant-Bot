import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import config
from bot.state import load_state, save_state, update_state
from scrapers.nightly_processor import run_nightly_job

# Tests for DATA-01
def test_cache_dir_centralization():
    assert str(config.CACHE_DIR).endswith("cache")
    # Check that main and memory_consolidation use it
    pass

# Tests for DATA-02
@pytest.mark.asyncio
async def test_nightly_queue_failure_handling(tmp_path):
    queue_file = tmp_path / "nightly_queue.json"
    queue_file.write_text(json.dumps([
        {"title": "Fail1", "file_id": "1"},
        {"title": "Success2", "file_id": "2"},
    ]))

    with patch("scrapers.nightly_processor.os.path.join") as mock_join:
        # Mock paths appropriately
        pass

# Tests for STATE-01
def test_update_state(tmp_path):
    config.STATE_FILE = tmp_path / "state.json"
    config.STATE_FILE.write_text(json.dumps({"seen_tasks": []}))

    def mutator(state):
        state["seen_tasks"].append("123")

    update_state(mutator)
    state = load_state()
    assert "123" in state["seen_tasks"]

import os
import pytest
from unittest import mock
import activity_log

@pytest.fixture
def patch_activity_log(tmp_path):
    log_file = tmp_path / "test_activity_log.jsonl"
    with mock.patch("activity_log.LOG_PATH", str(log_file)), \
         mock.patch("activity_log.MAX_LOG_SIZE", 100), \
         mock.patch("activity_log.MAX_ENTRIES", 5):
        yield log_file

def test_rotate_file_missing(patch_activity_log):
    # File doesn't exist, should return cleanly
    activity_log._rotate_if_needed()
    assert not patch_activity_log.exists()

def test_rotate_file_small(patch_activity_log):
    # Create file smaller than MAX_LOG_SIZE (100)
    data = "x" * 50
    patch_activity_log.write_text(data, encoding="utf-8")

    activity_log._rotate_if_needed()

    # Should not be modified
    assert patch_activity_log.read_text(encoding="utf-8") == data

def test_rotate_file_large_lines_small(patch_activity_log):
    # Create file >= 100 bytes, but only 3 lines (<= 5)
    data = "x" * 50 + "\n" + "y" * 50 + "\n" + "z" * 50 + "\n"
    patch_activity_log.write_text(data, encoding="utf-8")

    activity_log._rotate_if_needed()

    # Should not be modified
    assert patch_activity_log.read_text(encoding="utf-8") == data

def test_rotate_file_large_lines_large(patch_activity_log):
    # Create file >= 100 bytes, with 8 lines (> 5)
    lines = [f"line {i}\n" for i in range(8)]
    # pad first line to make file size > 100
    lines[0] = "x" * 100 + lines[0]

    patch_activity_log.write_text("".join(lines), encoding="utf-8")

    activity_log._rotate_if_needed()

    # Should keep exactly the last 5 lines
    result_lines = patch_activity_log.read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(result_lines) == 5
    assert result_lines == lines[-5:]

def test_rotate_exception_handling(patch_activity_log):
    # File large enough to trigger rotation read
    patch_activity_log.write_text("x" * 150, encoding="utf-8")

    # Mock open to raise exception
    with mock.patch("builtins.open", side_effect=OSError("Disk full")):
        # Should catch exception and return silently
        activity_log._rotate_if_needed()

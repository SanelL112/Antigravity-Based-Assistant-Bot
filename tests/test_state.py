import pytest
import datetime
from unittest.mock import patch
import pytz
from bot.state import is_sleep_window
from freezegun import freeze_time

def _run_with_time(hour, minute):
    """Helper to mock datetime and check if the given time in ET is considered a sleep window."""
    # Create the datetime in ET timezone first
    et_tz = pytz.timezone('US/Eastern')
    # Use localized time to ensure correct timezone arithmetic inside our freeze environment
    # But since freezegun intercepts datetime.now(tz), it needs to know what the current time is in UTC.
    dt_et = et_tz.localize(datetime.datetime(2023, 1, 1, hour, minute, 0))
    dt_utc = dt_et.astimezone(pytz.utc)

    with freeze_time(dt_utc):
        return is_sleep_window()

def test_is_sleep_window_before_start():
    # 0:59 AM ET is not in sleep window
    assert _run_with_time(0, 59) is False

def test_is_sleep_window_at_start():
    # 1:00 AM ET is in sleep window
    assert _run_with_time(1, 0) is True

def test_is_sleep_window_during():
    # 4:00 AM ET is in sleep window
    assert _run_with_time(4, 0) is True
    # 6:59 AM ET is in sleep window
    assert _run_with_time(6, 59) is True

def test_is_sleep_window_at_end():
    # 7:00 AM ET is NOT in sleep window
    assert _run_with_time(7, 0) is False

def test_is_sleep_window_after_end():
    # 12:00 PM ET is NOT in sleep window
    assert _run_with_time(12, 0) is False

def test_is_sleep_window_exception():
    # In bot/state.py:
    # try:
    #     import datetime
    #     import pytz
    #     ...
    # except Exception:
    #     return False
    # To test exception, we can mock `pytz.timezone` to raise an Exception when called from is_sleep_window
    with patch('pytz.timezone', side_effect=Exception("Mocked exception")):
        assert is_sleep_window() is False

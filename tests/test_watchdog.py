import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Since we auto-mocked env vars and mkdir in conftest.py, we can safely import main
import main

@pytest.mark.asyncio
async def test_watchdog_check_try_catch():
    """
    Test that watchdog_check handles exceptions from _watchdog_impl properly.
    It should not propagate the exception and the lock should be released.
    """
    # Create a dummy context
    context = MagicMock()

    # We want to force _watchdog_impl to raise an exception
    with patch("main._watchdog_impl", new_callable=AsyncMock) as mock_impl:
        mock_impl.side_effect = Exception("Intentional watchdog failure")

        # Ensure the lock is not locked initially
        assert not main.watchdog_lock.locked()

        # Call watchdog_check
        # Without try/except in watchdog_check, this will raise the Exception
        try:
            await main.watchdog_check(context)
            exception_raised = False
        except Exception as e:
            exception_raised = True
            assert str(e) == "Intentional watchdog failure"

        # The test itself checks if exception is caught by watchdog_check,
        # so exception_raised should be False when fixed
        # But wait, we want the test to assert that it DOESN'T raise.
        # So we assert not exception_raised
        assert not exception_raised, "watchdog_check should catch exceptions from _watchdog_impl"

        # Also ensure the lock is released
        assert not main.watchdog_lock.locked(), "watchdog_lock should be released even if exception occurs"

        mock_impl.assert_called_once_with(context)

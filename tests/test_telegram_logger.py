import logging
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_emit_queues_delivery_without_synchronous_network_io(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    import telegram_logger

    handler = telegram_logger.TelegramHandler()
    record = logging.LogRecord(
        name="app", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="database temporarily unavailable", args=(), exc_info=None,
    )

    with patch("telegram_logger.requests.post") as post:
        handler.emit(record)
        post.assert_not_called()

    assert handler.pending_count == 1

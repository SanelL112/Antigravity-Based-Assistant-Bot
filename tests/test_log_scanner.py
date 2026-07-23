import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import log_scanner


def test_activity_log_scanner_supports_all_timestamp_formats(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    entries = [
        {"ts": now.timestamp(), "cat": "error", "details": {"kind": "numeric"}},
        {
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M:%S"),
            "cat": "critical",
            "details": {"kind": "date-time"},
        },
        {"timestamp": "not-a-date", "cat": "error", "details": {"kind": "invalid"}},
    ]
    (tmp_path / "activity_log.jsonl").write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n"
    )
    monkeypatch.setattr(log_scanner, "BASE_DIR", tmp_path)

    matches = log_scanner.scan_activity_log(hours=1)

    assert [match["message"] for match in matches] == [
        '[error] {"kind": "numeric"}',
        '[critical] {"kind": "date-time"}',
    ]
    assert matches[1]["timestamp"] == f"{now.date().isoformat()} {now.strftime('%H:%M:%S')}"

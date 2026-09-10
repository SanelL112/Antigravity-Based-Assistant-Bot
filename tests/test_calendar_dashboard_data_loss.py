"""Regression and unit tests for calendar & dashboard data loss fixes.

Covers the 4 bugs and fixes documented in docs/2026-09-10_calendar_dashboard_data_loss_fix.md:
1. Canvas calendar window-anchored query and fallback.
2. Compaction line limit (8) and decorative header filtering.
3. Exact (title, date) duplicate suppression in deterministic digest.
4. Refresh-based deduplication with timestamps and legacy migration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
from unittest.mock import MagicMock, patch

import ai_processor
import scrapers.canvas_scraper as canvas_scraper


class TestCanvasCalendarWindow:
    def test_window_anchored_query_constructed(self):
        mock_canvas = MagicMock()
        mock_canvas.get_favorite_courses.return_value = [{"id": 42, "name": "AP Biology"}]
        calls = []

        def fake_get_paginated(url, max_pages=1):
            calls.append(url)
            if "assignments" in url:
                return [{
                    "id": 101,
                    "name": "Enzyme Lab Final Draft",
                    "due_at": "2026-09-11T23:59:00Z",
                    "html_url": "https://canvas.example.com/item",
                }]
            return []

        mock_canvas.get_paginated = fake_get_paginated
        with patch.dict(os.environ, {"CANVAS_CALENDAR_WINDOW_DAYS": "180", "CANVAS_ASSIGNMENT_OVERDUE_GRACE_DAYS": "7"}):
            results = canvas_scraper._get_calendar_assignments(mock_canvas)

        assignment_calls = [c for c in calls if "assignments" in c]
        assert len(assignment_calls) == 1
        query = assignment_calls[0]
        assert "due_at[" in query
        assert "order_by=due_at" in query
        assert "order=asc" in query
        assert any(r["title"] == "Enzyme Lab Final Draft" for r in results)

    def test_window_query_fallback_when_empty(self):
        mock_canvas = MagicMock()
        mock_canvas.get_favorite_courses.return_value = [{"id": 42, "name": "AP Biology"}]
        calls = []

        def fake_get_paginated(url, max_pages=1):
            calls.append(url)
            if "due_at[" in url:
                return []
            if "assignments" in url:
                return [{
                    "id": 102,
                    "name": "Fallback Assignment",
                    "due_at": "2026-09-15T23:59:00Z",
                    "html_url": "https://canvas.example.com/fallback",
                }]
            return []

        mock_canvas.get_paginated = fake_get_paginated
        results = canvas_scraper._get_calendar_assignments(mock_canvas)
        assignment_calls = [c for c in calls if "assignments" in c]
        assert len(assignment_calls) == 2, "Must retry without due_at range when window query returns empty"
        assert "due_at[" in assignment_calls[0]
        assert "due_at[" not in assignment_calls[1]
        assert any(r["title"] == "Fallback Assignment" for r in results)


class TestDigestCompaction:
    def test_default_limit_is_eight(self):
        sample = "\n".join(f"- Item {i}" for i in range(15))
        lines = ai_processor._compact_digest_lines(sample)
        assert len(lines) == 8

    def test_drops_decorative_headers_and_preserves_content(self):
        raw = """
        🎯 **Canvas: What to do next**
        🚨 **Missing / overdue**
        - [AP Bio] Quiz 1 — Due: 2026-08-14
        - [AP Bio] Quiz 2 — Due: 2026-08-14
        📅 **Due soon**
        - [AP Bio] Enzyme lab final draft — Due: 2026-09-11
        ✅ **Recently completed**
        - [AP Bio] Pre-lab assignment
        📢 **Canvas Announcements:**
        - Please remember to bring safety goggles
        """
        lines = ai_processor._compact_digest_lines(raw, limit=8)
        assert not any("What to do next" in l for l in lines)
        assert not any(l == "**Missing / overdue**" for l in lines)
        assert not any(l == "**Due soon**" for l in lines)
        assert not any(l == "**Recently completed**" for l in lines)
        assert not any(l == "**Canvas Announcements:**" for l in lines)

        # Content must survive
        assert any("Quiz 1" in l for l in lines)
        assert any("Enzyme lab final draft" in l for l in lines)
        assert any("Pre-lab assignment" in l for l in lines)
        assert any("safety goggles" in l for l in lines)


class TestDeterministicDigestDeduplication:
    def test_suppresses_only_highlighted_title_date_pairs(self):
        # 6 tasks in window: first 5 go to Needs attention, 6th is beyond cap.
        # Overdue item is older than 7 days, so it is not in Needs attention.
        summaries = {
            "canvas": """
- [AP Bio] Task 1 — Due: 2026-09-11
- [AP Bio] Task 2 — Due: 2026-09-12
- [AP Bio] Task 3 — Due: 2026-09-13
- [AP Bio] Task 4 — Due: 2026-09-14
- [AP Bio] Task 5 — Due: 2026-09-15
- [AP Bio] Task 6 (Beyond cap) — Due: 2026-09-16
- [AP Bio] Overdue 0.1 Academic Integrity — Due: 2026-08-14 · Overdue
"""
        }
        digest, tasks = ai_processor._deterministic_digest(summaries)
        assert "⚡ **Needs attention**" in digest
        assert "📚 **Canvas**" in digest

        needs_attention = digest.split("📚 **Canvas**")[0]
        canvas_section = digest.split("📚 **Canvas**")[1]

        # Tasks 1-5 are highlighted in Needs attention
        for i in range(1, 6):
            assert f"Task {i} — due" in needs_attention
            # And deduplicated out of Canvas section
            assert f"Task {i}" not in canvas_section

        # Task 6 and Overdue task survive in Canvas section
        assert "Task 6 (Beyond cap)" in canvas_section
        assert "Overdue 0.1 Academic Integrity" in canvas_section


class TestSeenBulletsRefreshAndMigration:
    def test_legacy_list_migration_and_recurring_preservation(self, tmp_path):
        seen_path = tmp_path / "seen_bullets.json"
        latest_path = tmp_path / "latest_digest.txt"

        with patch("ai_processor.CACHE_DIR", tmp_path), patch("ai_processor.LATEST_DIGEST_FILE", latest_path):
            legacy_bullets = ["enzyme lab final draft due 20260911", "old task"]
            seen_path.write_text(json.dumps(legacy_bullets))

            summary = {"canvas": "• Enzyme lab final draft — Due: 2026-09-11\n• Brand new task"}
            result = ai_processor.assemble_digest(summary)

            # File must be converted to dict format
            persisted = json.loads(seen_path.read_text())
            assert isinstance(persisted, dict)
            assert "enzyme lab final draft  due 20260911" in persisted or any("enzyme" in k for k in persisted)

            # Recurring bullet must remain in output digest (not suppressed forever)
            assert "Enzyme lab final draft" in result["digest"]
            assert "Brand new task" in result["digest"]

            # Backward compatibility check: set(json.loads(...)) on dict yields keys
            as_set = set(persisted)
            assert any("enzyme" in k for k in as_set)

    def test_stale_bullets_pruned_and_cap_eviction(self, tmp_path):
        seen_path = tmp_path / "seen_bullets.json"
        latest_path = tmp_path / "latest_digest.txt"

        with patch("ai_processor.CACHE_DIR", tmp_path), patch("ai_processor.LATEST_DIGEST_FILE", latest_path):
            now = time.time()
            stale_data = {
                "stale bullet": now - 10 * 86400,  # 10 days old (> 7 day default)
                "fresh bullet": now - 1 * 86400,
            }
            seen_path.write_text(json.dumps(stale_data))

            ai_processor.assemble_digest({})
            persisted = json.loads(seen_path.read_text())
            assert "stale bullet" not in persisted
            assert "fresh bullet" in persisted

            # Cap eviction (> 5000 entries)
            bulk_data = {f"b_{i}": now + i for i in range(5050)}
            seen_path.write_text(json.dumps(bulk_data))
            ai_processor.assemble_digest({})
            persisted_bulk = json.loads(seen_path.read_text())
            assert len(persisted_bulk) == 5000
            assert "b_0" not in persisted_bulk
            assert "b_5049" in persisted_bulk

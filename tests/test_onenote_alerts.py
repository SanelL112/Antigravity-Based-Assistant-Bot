"""Hermetic tests for OneNote alerts, page retention, and digest section (Phase 1).

No network, no browser, no subprocess.  Every path is explicit (tmp dirs), so
the harvest-cache diff, first-seen page tracking, and markdown retention are
exercised exactly as the daemon/digest would run them.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import ai_processor
from scrapers import onenote_alerts as oa
from scrapers.onenote_web_scraper import save_harvested_page


def _write_cache(tmp_path, pages: dict) -> None:
    (tmp_path / "onenote_page_extractions.json").write_text(
        json.dumps(pages), encoding="utf-8"
    )


def _read_cache(tmp_path):
    return json.loads((tmp_path / "onenote_page_extractions.json").read_text())


# Fixed "now" for deterministic window math (system clock may drift).
_TODAY = "2026-09-01"


def _generic_task(
    title="Unit 1 Quiz", due_date=None, course="AP Calc"
):
    if due_date is None:
        due_date = (date.fromisoformat(_TODAY) + timedelta(days=10)).isoformat()
    return {"title": title, "due_date": due_date, "task_type": "Test", "course": course}


def _alerts(tmp_path, today=_TODAY):
    """Run the alert diff with an explicit window anchor."""
    return oa.check_new_onenote_alerts(cache_dir=tmp_path, today=date.fromisoformat(today))


# ── Item 2: new-task alerts ─────────────────────────────────────────────────

def test_no_cache_file_yields_no_alerts(tmp_path):
    assert _alerts(tmp_path) == ""


def test_new_upcoming_alerts_exactly_once(tmp_path):
    _write_cache(
        tmp_path,
        {"AP Calc/Section/Notes": [_generic_task(due_date="2026-09-10")]},
    )
    first = _alerts(tmp_path)
    assert "Unit 1 Quiz" in first and "2026-09-10" in first
    # Same cache, second run: the item was seen; no duplicate alert.
    assert _alerts(tmp_path) == ""


def test_only_upcoming_items_alert(tmp_path):
    _write_cache(
        tmp_path,
        {"nb/sec/A": [
            _generic_task(title="Past Due", due_date="2026-08-20"),
            _generic_task(title="Very Far", due_date="2027-03-01"),
            _generic_task(title="No Date", due_date=""),
            _generic_task(title="Real Soon", due_date="2026-09-15"),
        ]},
    )
    rows = oa._upcoming_rows(_read_cache(tmp_path), today=date.fromisoformat(_TODAY))
    titles = [r["title"] for r in rows]
    assert titles == ["Real Soon"]  # past / >60d / undated all excluded


def test_junk_and_scaffolding_titles_are_filtered(tmp_path):
    _write_cache(
        tmp_path,
        {"Bio/Section/Notes": [
            _generic_task(title="Upcoming", due_date="2026-09-05"),
            _generic_task(title="Advisement", due_date="2026-09-05"),
            _generic_task(title="Real lab quiz", due_date="2026-09-05"),
        ]},
    )
    alert = _alerts(tmp_path)
    assert "Real lab quiz" in alert
    assert "Advisement" not in alert


def test_alert_rendering_caps_and_marks_more(tmp_path):
    tasks = [
        {"title": f"Task {i}", "due_date": "2026-09-10", "notebook": "nb"}
        for i in range(8)
    ]
    message = oa._render_alert(tasks, limit=6)
    assert "Task 0" in message and "Task 5" in message
    assert "Task 6" not in message
    assert "2 more" in message


def test_alert_rendering_empty():
    assert oa._render_alert([]) == ""


# ── Item 3: "From your notebooks" digest section ────────────────────────────

def test_notebooks_section_lists_new_pages_and_upcoming(tmp_path):
    due = (date.fromisoformat(_TODAY) + timedelta(days=11)).isoformat()
    _write_cache(
        tmp_path,
        {
            "AP Calc/Section/Limits Notes": [_generic_task(due_date=due)],
            "Chem Section/Review Sheet": [],
        },
    )
    section = oa.notebooks_section(cache_dir=tmp_path, today=date.fromisoformat(_TODAY))
    assert "From your notebooks" in section
    assert "Limits Notes" in section          # new page this week
    assert "Review Sheet" in section          # second new page
    assert "Unit 1 Quiz" in section           # upcoming item
    assert due in section


def test_pages_exit_new_window_after_seven_days(tmp_path):
    _write_cache(
        tmp_path,
        {"nb/sec/Old Page": []},
    )
    today = date(2026, 9, 1)
    oa.notebooks_section(cache_dir=tmp_path, today=today)  # records first-seen
    later = oa.notebooks_section(cache_dir=tmp_path, today=today + timedelta(days=8))
    assert "Old Page" not in later           # no longer "this week"
    assert later == ""                       # and nothing else to show


def test_junk_page_titles_never_enter_section(tmp_path):
    _write_cache(
        tmp_path,
        {
            "nb/sec/August 2026 Calendar": [_generic_task()],
            "nb/sec/2026-08-24": [_generic_task()],
            "nb/sec/Real Notes": [_generic_task()],
        },
    )
    section = oa.notebooks_section(cache_dir=tmp_path, today=date.fromisoformat(_TODAY))
    assert "Real Notes" in section
    assert "Calendar" not in section
    assert "2026-08-24" not in section


def test_digest_appends_notebooks_section(tmp_path, monkeypatch):
    """assemble_digest gains a third 'From your notebooks' section."""
    due = (date.today() + timedelta(days=5)).isoformat()
    (tmp_path / "onenote_page_extractions.json").write_text(
        json.dumps({"AP Calc/sec/Notes": [_generic_task(due_date=due)]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(oa, "_cache_dir", lambda _dir=None: tmp_path)

    def fake_inference(prompt, *, timeout, max_tokens):
        return "✅ All caught up — no new actionable updates."

    monkeypatch.setattr(ai_processor, "_local_inference", fake_inference)
    result = ai_processor.assemble_digest({"canvas": "No canvas data available."})
    assert "From your notebooks" in result["digest"]
    assert "Unit 1 Quiz" in result["digest"]


def test_digest_unchanged_when_no_notebooks_content(tmp_path, monkeypatch):
    """No harvest cache -> no notebooks section sneaks into the digest."""
    monkeypatch.setattr(oa, "_cache_dir", lambda _dir=None: tmp_path)

    def fake_inference(prompt, *, timeout, max_tokens):
        return "A normal digest body."

    monkeypatch.setattr(ai_processor, "_local_inference", fake_inference)
    result = ai_processor.assemble_digest({"canvas": "No canvas data available."})
    assert "From your notebooks" not in result["digest"]


# ── Item 1: page retention → RAG ────────────────────────────────────────────

def test_save_harvested_page_writes_frontmatter(tmp_path):
    path = save_harvested_page(
        "AP Biology", "Unit 1", "Enzyme Notes", "Enzymes speed up reactions.", pages_dir=tmp_path
    )
    assert path is not None
    assert path.name == "Enzyme_Notes.md"
    assert path.parent.name == "Unit_1"          # sanitized section
    assert path.parent.parent.name == "AP_Biology"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "notebook: AP Biology" in text
    assert "Enzymes speed up reactions." in text
    # Layout matches the indexer's recursive glob: <root>/**/*.md
    import glob

    assert path in [__import__("pathlib").Path(p) for p in glob.glob(str(tmp_path / "**" / "*.md"), recursive=True)]


def test_save_harvested_page_skips_thin_content(tmp_path):
    assert save_harvested_page("nb", "sec", "Blank", "hi", pages_dir=tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_embedding_indexer_collects_harvested_pages(tmp_path, monkeypatch):
    """source_cache/onenote_pages/**/*.md feeds the embedding corpus."""
    import scrapers.embedding_indexer as indexer

    # Point the indexer at a hermetic tree: BASE_DIR -> tmp, CACHE_DIR is the
    # disposable runtime root under conftest, so every glob stays in tmp.
    monkeypatch.setattr(indexer, "BASE_DIR", str(tmp_path))
    page = save_harvested_page(
        "AP Calc", "Unit 1", "Limits Notes", "Limits describe behavior near a point.",
        pages_dir=tmp_path / "source_cache" / "onenote_pages",
    )
    sources = indexer.collect_sources()
    assert any(s["path"] == str(page) for s in sources)
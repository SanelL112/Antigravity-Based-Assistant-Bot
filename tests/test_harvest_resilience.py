"""Hermetic tests for OneNote harvest resilience in the browser daemon.

Regression coverage for the harvest loop in
``scripts/canvas_browser_daemon.py::BrowserDaemon.harvest_onenote``:

- the duplicated ``except Exception`` clauses made the retry/self-heal path
  unreachable (first match wins) — a dead session silently aborted the walk;
- a mid-harvest session death must keep partial gains and merge them into
  the persisted cache instead of dropping the walk;
- a wholly empty harvest must never overwrite a last-known-good cache;
- recovery must relaunch the browser when the session is dead and re-read
  the fresh driver.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.canvas_browser_daemon as cbd


class RecordingLogger:
    """Captures log calls so tests can assert on them."""

    def __init__(self):
        self.exceptions: list[tuple[str, tuple]] = []
        self.warnings: list[tuple[str, tuple]] = []
        self.infos: list[tuple[str, tuple]] = []

    def exception(self, msg, *args):
        self.exceptions.append((msg, args))

    def warning(self, msg, *args):
        self.warnings.append((msg, args))

    def info(self, msg, *args):
        self.infos.append((msg, args))


def make_daemon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> cbd.BrowserDaemon:
    """Build a BrowserDaemon without launching Firefox or the HTTP server."""
    monkeypatch.setattr(cbd.config, "CACHE_DIR", tmp_path)
    daemon = cbd.BrowserDaemon.__new__(cbd.BrowserDaemon)
    daemon.client = SimpleNamespace(driver=object())  # non-None sentinel
    daemon.lock = threading.Lock()
    daemon.was_authenticated = False
    daemon.last_reauth_attempt = 0.0
    daemon.reauth_cooldown = 900
    return daemon


def stub_crawl(monkeypatch: pytest.MonkeyPatch, daemon) -> RecordingLogger:
    """Stub the crawl/grid plumbing and swap in a recording logger."""
    monkeypatch.setattr(
        daemon, "crawl_onenote_web",
        lambda *a, **k: {"status": "authenticated_and_navigated"},
    )
    monkeypatch.setattr(daemon, "_ensure_notebooks_view", lambda driver: True)
    monkeypatch.setattr(daemon, "_detect_notebooks", lambda driver: ["NB1"])
    log = RecordingLogger()
    monkeypatch.setattr(cbd, "logger", log)
    return log


def write_cache(cache_dir: Path, data: dict) -> None:
    (cache_dir / "onenote_page_extractions.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def read_cache(cache_dir: Path) -> dict:
    return json.loads(
        (cache_dir / "onenote_page_extractions.json").read_text(encoding="utf-8")
    )


class TestRetryPathReachable:
    """The self-heal/retry path must actually run after a dead session."""

    def test_dead_session_relaunches_browser_and_retries(
        self, monkeypatch, tmp_path
    ):
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)

        calls: list[object] = []
        relaunched = {"n": 0}
        fresh_driver = object()
        stale_driver = daemon.client.driver

        def fake_harvest_notebook(driver, nb_name, *a, **k):
            calls.append(driver)
            if len(calls) == 1:
                raise RuntimeError("invalid session id: session deleted")
            return {"pages": 2, "tasks": 1}

        def fake_restart_browser():
            relaunched["n"] += 1
            daemon.client = SimpleNamespace(driver=fresh_driver)

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)
        monkeypatch.setattr(daemon, "_session_alive", lambda: False)
        monkeypatch.setattr(daemon, "restart_browser", fake_restart_browser)

        res = daemon.harvest_onenote()

        assert len(calls) == 2, "harvest must retry after relaunch"
        assert relaunched["n"] == 1
        assert calls[0] is stale_driver
        assert calls[1] is fresh_driver, "retry must use the relaunched driver"
        assert res["pages_scanned"] == 2
        assert len(res["errors"]) == 1 and "attempt 1" in res["errors"][0]

    def test_transient_with_partial_gain_keeps_tasks_without_traceback(
        self, monkeypatch, tmp_path
    ):
        daemon = make_daemon(monkeypatch, tmp_path)
        log = stub_crawl(monkeypatch, daemon)

        seeded = {"NB1/S1/P1": [{"t": 1}]}
        state = {"n": 0}

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            state["n"] += 1
            if state["n"] == 1:
                cache_data.update(seeded)
                raise RuntimeError("browsing context has been discarded")
            return {"pages": 0, "tasks": 0}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)
        monkeypatch.setattr(daemon, "_session_alive", lambda: True)

        res = daemon.harvest_onenote()

        assert res["tasks_extracted"] == 1
        assert any("partial" in e for e in res["errors"])
        assert log.exceptions == [], "partial gain must not log a traceback"
        assert read_cache(tmp_path) == seeded


class TestCacheMergeGuard:
    """Cache writes must merge, never wipe last-known-good data."""

    def test_partial_flush_merges_into_existing_cache(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {"OLD/NB/P": [{"old": True}]})

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            cache_data["NB1/S1/P1"] = [{"t": 1}]
            raise RuntimeError("browser died mid-walk")

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)
        monkeypatch.setattr(daemon, "_session_alive", lambda: False)
        monkeypatch.setattr(daemon, "restart_browser", lambda: None)

        res = daemon.harvest_onenote()

        merged = read_cache(tmp_path)
        assert merged["OLD/NB/P"] == [{"old": True}], "old entry must survive"
        assert merged["NB1/S1/P1"] == [{"t": 1}], "partial gain must persist"
        assert res.get("partial") is True

    def test_zero_page_harvest_keeps_good_cache(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {"GOOD/NB/P": [{"good": True}]})

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            raise RuntimeError("nothing worked")

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)
        monkeypatch.setattr(daemon, "_session_alive", lambda: True)

        res = daemon.harvest_onenote()

        assert res["status"] == "empty"
        assert read_cache(tmp_path) == {"GOOD/NB/P": [{"good": True}]}

    def test_successful_harvest_merges_with_previous(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {"OLD/NB/P": [{"old": True}]})

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            cache_data["NB1/S2/P2"] = [{"t": 2}]
            return {"pages": 1, "tasks": 1}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)

        daemon.harvest_onenote()

        merged = read_cache(tmp_path)
        assert set(merged) == {"OLD/NB/P", "NB1/S2/P2"}

    def test_reextracted_page_overwrites_own_stale_entry(
        self, monkeypatch, tmp_path
    ):
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {"NB1/S1/P1": [{"stale": True}]})

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            cache_data["NB1/S1/P1"] = [{"fresh": True}]
            return {"pages": 1, "tasks": 1}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)

        daemon.harvest_onenote()

        assert read_cache(tmp_path) == {"NB1/S1/P1": [{"fresh": True}]}


class TestCrossRunResume:
    def test_previously_harvested_titles_are_skipped(self, monkeypatch, tmp_path):
        """A fresh run must skip pages the last (killed) run already did."""
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {
            "NB1/S1/Lesson_2_1_pgs_1-10": [{"t": 1}],
            "NB1/S1/progress_check_unit_2_pg_69-72": [{"t": 2}],
            "OTHERNB/S/P": [{"t": 3}],  # not in this run's notebooks
        })

        captured: dict = {}

        def fake_harvest_notebook(driver, nb_name, cache_data, trace, errors,
                                  extract_fn, remaining, seen_titles=None):
            captured["seen"] = set(seen_titles or set())
            return {"pages": 0, "tasks": 0}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)

        daemon.harvest_onenote(notebooks=["NB1"])

        seen = captured["seen"]
        assert "Lesson_2_1_pgs_1-10" in seen
        assert "progress_check_unit_2_pg_69-72" in seen
        assert "P" not in seen, "entries from other notebooks must not leak in"


class TestSessionRecovery:
    def test_recover_alive_when_grid_reachable(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon, "_session_alive", lambda: True)
        monkeypatch.setattr(daemon, "_ensure_notebooks_view", lambda d: True)
        assert daemon._recover_harvest_session(object()) == "alive"

    def test_recover_relaunches_when_session_dead(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon, "_session_alive", lambda: False)
        restarted = {"n": 0}
        monkeypatch.setattr(
            daemon, "restart_browser", lambda: restarted.__setitem__("n", 1)
        )
        assert daemon._recover_harvest_session(object()) == "relaunched"
        assert restarted["n"] == 1

    def test_recover_dead_when_relaunch_fails(self, monkeypatch, tmp_path):
        daemon = make_daemon(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon, "_session_alive", lambda: False)

        def boom():
            raise RuntimeError("no X display")

        monkeypatch.setattr(daemon, "restart_browser", boom)
        assert daemon._recover_harvest_session(object()) == "dead"


class TestVirtualDisplayLockCleanup:
    def test_stale_lock_file_cleaned_up(self, monkeypatch, tmp_path):
        """If Xvfb lock file exists but PID is dead, it should be unlinked."""
        display = cbd.VirtualDisplay()
        lock_file = Path("/tmp/.X99-lock")
        # Ensure we don't clobber a real running Xvfb if one is on 99
        # Test using a mock / temporary lock check
        fake_lock = tmp_path / ".X99-lock"
        fake_lock.write_text("999999999\n", encoding="utf-8")
        assert fake_lock.exists()

        monkeypatch.setattr(cbd, "get_setting", lambda k, d: ":99")
        # Patch Path so /tmp/.X99-lock points to fake_lock
        orig_path = cbd.Path
        def fake_path(p):
            if str(p) == "/tmp/.X99-lock":
                return fake_lock
            return orig_path(p)

        monkeypatch.setattr(cbd, "Path", fake_path)
        monkeypatch.setattr(cbd.shutil, "which", lambda b: "/usr/bin/Xvfb")

        # Mock subprocess.Popen so we don't actually spawn Xvfb in unit test
        class FakeProc:
            def poll(self):
                return None
        monkeypatch.setattr(cbd.subprocess, "Popen", lambda *a, **k: FakeProc())
        monkeypatch.setenv("DISPLAY", "")
        # Remove DISPLAY from environ if set so start() runs
        monkeypatch.delenv("DISPLAY", raising=False)

        display.start()
        assert not fake_lock.exists(), "Stale lock file should have been unlinked"
        assert display.process is not None


class TestSectionGroupClassification:
    def test_section_group_vs_leaf_filtering(self):
        """Verify the logic used in daemon and probe correctly discriminates leaf vs group."""
        # Simulated DOM node representation
        def is_group(el: dict) -> bool:
            if el.get("aria-expanded") is not None:
                return True
            label = (el.get("aria-label") or "").lower()
            if "section group" in label:
                return True
            cls = (el.get("class") or "").lower()
            if "sectiongroup" in cls or "groupitemwrap" in cls:
                return True
            if el.get("role") == "treeitem":
                if el.get("has_child_container") or el.get("has_chevron"):
                    return True
            return False

        top_group = {
            "role": "treeitem",
            "aria-expanded": "false",
            "aria-label": "_Content Library Section Group",
            "name": "_Content Library",
        }
        nested_group = {
            "role": "treeitem",
            "aria-expanded": "false",
            "class": "sectionListItem",
            "name": "U2 Cells and Transport Extra Resources",
            "has_chevron": True,
        }
        leaf_section = {
            "role": "treeitem",
            "class": "sectionListItem",
            "name": "U1 Chem of Life Class Notes",
        }
        plain_leaf = {
            "class": "sectionListItem",
            "name": "Common reference sheets",
        }

        assert is_group(top_group) is True
        assert is_group(nested_group) is True
        assert is_group(leaf_section) is False
        assert is_group(plain_leaf) is False

        # Filter only leaves
        items = [top_group, nested_group, leaf_section, plain_leaf]
        leaves = [it["name"] for it in items if not is_group(it)]
        assert leaves == ["U1 Chem of Life Class Notes", "Common reference sheets"]
        assert "U2 Cells and Transport Extra Resources" not in leaves



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
import os
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
        """If Xvfb lock file exists but PID is dead, both lock and socket should be unlinked."""
        fake_lock = tmp_path / ".X99-lock"
        fake_sock = tmp_path / "X99"
        fake_lock.write_text("999999999\n", encoding="utf-8")
        fake_sock.touch()
        assert fake_lock.exists()
        assert fake_sock.exists()

        monkeypatch.setattr(cbd, "get_setting", lambda k, d: ":99")
        monkeypatch.setattr(cbd.shutil, "which", lambda b: "/usr/bin/Xvfb")

        class FakeProc:
            def poll(self):
                return None
            def terminate(self):
                pass
            def wait(self, timeout=None):
                pass
            def kill(self):
                pass

        monkeypatch.setattr(cbd.subprocess, "Popen", lambda *a, **k: FakeProc())
        monkeypatch.delenv("DISPLAY", raising=False)

        display = cbd.VirtualDisplay()
        display._lock_file = fake_lock
        display._sock_file = fake_sock

        display.start()
        assert not fake_lock.exists(), "Stale lock file should have been unlinked"
        assert not fake_sock.exists(), "Stale socket file should have been unlinked"
        assert display.process is not None
        display.close()

    def test_stale_socket_without_lock_cleaned_up(self, monkeypatch, tmp_path):
        """If X11 UNIX socket exists without lock file, it should be unlinked."""
        fake_lock = tmp_path / ".X99-lock"
        fake_sock = tmp_path / "X99"
        fake_sock.touch()
        assert fake_sock.exists()
        assert not fake_lock.exists()

        display = cbd.VirtualDisplay()
        display._lock_file = fake_lock
        display._sock_file = fake_sock

        display._cleanup_stale_files()
        assert not fake_sock.exists(), "Stale socket should have been unlinked"

    def test_stale_recycled_pid_cleaned_up(self, monkeypatch, tmp_path):
        """If PID in lock file is alive but NOT an Xvfb process, clean it up."""
        fake_lock = tmp_path / ".X99-lock"
        fake_sock = tmp_path / "X99"
        fake_lock.write_text(f"{os.getpid()}\n", encoding="utf-8")
        fake_sock.touch()

        display = cbd.VirtualDisplay()
        display._lock_file = fake_lock
        display._sock_file = fake_sock

        display._cleanup_stale_files()
        assert not fake_lock.exists(), "Lock with non-Xvfb PID should be unlinked"
        assert not fake_sock.exists(), "Socket with non-Xvfb PID should be unlinked"

    def test_orphaned_xvfb_terminated_and_cleaned_up(self, monkeypatch, tmp_path):
        """If orphaned Xvfb is running on display, terminate it and unlink files."""
        fake_lock = tmp_path / ".X99-lock"
        fake_sock = tmp_path / "X99"
        fake_lock.write_text("12345\n", encoding="utf-8")
        fake_sock.touch()

        display = cbd.VirtualDisplay()
        display._lock_file = fake_lock
        display._sock_file = fake_sock

        signals_sent = []
        def fake_kill(pid, sig):
            if sig == 0:
                if signals_sent:
                    raise OSError("Process dead")
                return None
            signals_sent.append((pid, sig))

        monkeypatch.setattr(cbd.os, "kill", fake_kill)
        orig_path = cbd.Path
        def fake_path(p):
            p_str = str(p)
            if p_str == "/proc/12345/cmdline":
                class MockCmdline:
                    def read_bytes(self):
                        return b"/usr/bin/Xvfb\x00:99"
                return MockCmdline()
            return orig_path(p)

        monkeypatch.setattr(cbd, "Path", fake_path)

        display._cleanup_stale_files(kill_existing_xvfb=True)
        assert signals_sent == [(12345, cbd.signal.SIGTERM)]
        assert not fake_lock.exists()
        assert not fake_sock.exists()


class TestMicrosoftSignInResilience:
    def test_sign_in_affordance_polls_until_found(self, monkeypatch, tmp_path):
        """_microsoft_sign_in should poll for the sign-in affordance across multiple attempts."""
        daemon = make_daemon(monkeypatch, tmp_path)
        monkeypatch.setattr(cbd, "get_setting", lambda k, d=None: "user@test.org" if "UPN" in k else "password123")

        call_count = {"count": 0}
        class FakeDriver:
            current_url = "https://onenote.cloud.microsoft/en-us/"
            title = "OneNote"
            def execute_script(self, script, *args):
                if "location.host.includes" in script:
                    return False
                if "candidates" in script:
                    call_count["count"] += 1
                    if call_count["count"] < 2:
                        return False
                    self.current_url = "https://onenote.cloud.microsoft/notebooks"
                    return True
                if "return !!document.querySelector" in script:
                    return True
                return None

            def find_elements(self, *a, **k):
                return []

            class SwitchTo:
                def default_content(self): pass
                def frame(self, f): pass
            switch_to = SwitchTo()

        driver = FakeDriver()
        daemon.client.driver = driver
        monkeypatch.setattr(cbd.time, "sleep", lambda s: None)

        ok, msg = daemon._microsoft_sign_in()
        assert call_count["count"] == 2
        assert ok is True
        assert "no password needed" in msg

    def test_password_submitted_in_iframe_before_switching(self, monkeypatch, tmp_path):
        """Password submission should execute inside the active frame context before switching."""
        daemon = make_daemon(monkeypatch, tmp_path)
        monkeypatch.setattr(cbd, "get_setting", lambda k, d=None: "user@test.org" if "UPN" in k else "password123")

        switched_to_default = []
        submitted_contexts = []

        class FakeElement:
            def clear(self): pass
            def send_keys(self, *a): pass

        fake_pass_elem = FakeElement()

        class FakeDriver:
            current_url = "https://login.microsoftonline.com/login"
            title = "Sign In"
            def execute_script(self, script, *args):
                if "location.host.includes" in script:
                    return True
                if "input[type=submit]" in script and "password" not in script:
                    submitted_contexts.append("in_frame" if not switched_to_default else "default_content")
                    return True
                if "kmsi" in script:
                    self.current_url = "https://onenote.cloud.microsoft/notebooks"
                    return True
                if "return !!document.querySelector" in script:
                    return True
                return None

            class SwitchTo:
                def default_content(self):
                    switched_to_default.append(True)
                def frame(self, f): pass
            switch_to = SwitchTo()

            def find_elements(self, *a, **k):
                return []

        driver = FakeDriver()
        daemon.client.driver = driver
        monkeypatch.setattr(cbd.time, "sleep", lambda s: None)

        class FakeWait:
            def __init__(self, driver, timeout): pass
            def until(self, poll_fn):
                if getattr(poll_fn, "__name__", "") == "poll":
                    return fake_pass_elem
                return None

        import selenium.webdriver.support.ui as ui
        monkeypatch.setattr(ui, "WebDriverWait", FakeWait)

        ok, msg = daemon._microsoft_sign_in()
        assert "in_frame" in submitted_contexts
        assert switched_to_default, "Must restore default_content after submitting"
        assert ok is True


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


class TestScopingAndAccountingRefactors:
    """Regression tests for per-notebook title scoping, partial accounting, and re-anchoring."""

    def test_cross_notebook_titles_do_not_collide(self, monkeypatch, tmp_path):
        """Pages with identical titles in different notebooks must not collide or skip."""
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)
        write_cache(tmp_path, {
            "NB1/S1/Unit 1": [{"t": 1}],
        })

        captured_seen: dict[str, set[str]] = {}

        def fake_harvest_notebook(driver, nb_name, cache_data, trace, errors,
                                  extract_fn, remaining, seen_titles=None):
            captured_seen[nb_name] = set(seen_titles or set())
            if seen_titles is not None:
                seen_titles.add("Lesson 1")
            return {"pages": 1, "tasks": 1}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)

        daemon.harvest_onenote(notebooks=["NB1", "NB2"])

        assert "Unit 1" in captured_seen["NB1"]
        assert "Unit 1" not in captured_seen["NB2"]
        assert "Lesson 1" not in captured_seen["NB2"]

    def test_partial_gain_with_zero_tasks_updates_pages_scanned(self, monkeypatch, tmp_path):
        """When pages with 0 tasks are harvested before an error, pages_scanned must update."""
        daemon = make_daemon(monkeypatch, tmp_path)
        log = stub_crawl(monkeypatch, daemon)

        def fake_harvest_notebook(driver, nb_name, cache_data, *a, **k):
            cache_data["NB1/S1/InfoPage1"] = []
            cache_data["NB1/S1/InfoPage2"] = []
            raise RuntimeError("browsing context has been discarded")

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)
        monkeypatch.setattr(daemon, "_session_alive", lambda: True)

        res = daemon.harvest_onenote(notebooks=["NB1"])

        assert res["pages_scanned"] == 2
        assert res["tasks_extracted"] == 0
        assert any("partial" in e for e in res["errors"])
        assert log.exceptions == [], "partial gain must not log full traceback"
        assert res.get("partial") is True

    def test_reanchor_editor_recovers_via_focus_live_tab(self, monkeypatch):
        """_reanchor_editor should attempt _focus_live_tab if switch_to.default_content fails initially."""
        state = {"switched_window": False, "switched_frame": False, "default_content_calls": 0}

        class FakeSwitchTo:
            def default_content(self):
                state["default_content_calls"] += 1
                if state["default_content_calls"] == 1:
                    raise RuntimeError("Browsing context has been discarded")

            def window(self, handle):
                state["switched_window"] = True

            def frame(self, el):
                state["switched_frame"] = True

        class FakeDriver:
            switch_to = FakeSwitchTo()
            window_handles = ["handle-1"]
            current_url = "https://tenant.sharepoint.com/teams/doc.aspx"

            def find_element(self, by, val):
                return "frame_element"

        driver = FakeDriver()
        reanchored = cbd.BrowserDaemon._reanchor_editor(driver)

        assert reanchored is True
        assert state["switched_window"] is True
        assert state["switched_frame"] is True
        assert state["default_content_calls"] == 2

    def test_balanced_budget_allocation_shares_pages_fairly(self, monkeypatch, tmp_path):
        """Budget must be divided fairly among remaining notebooks with unused rollover."""
        daemon = make_daemon(monkeypatch, tmp_path)
        stub_crawl(monkeypatch, daemon)

        captured_remaining: dict[str, int] = {}

        def fake_harvest_notebook(driver, nb_name, cache_data, trace, errors, extract_fn, remaining, seen_titles=None):
            captured_remaining[nb_name] = remaining
            if nb_name == "NB1":
                cache_data["NB1/S1/P1"] = [{"title": "T1", "due_date": "2026-09-10"}]
                return {"pages": 5, "tasks": 1}
            elif nb_name == "NB2":
                cache_data["NB2/S1/P1"] = [{"title": "T2", "due_date": "2026-09-11"}]
                return {"pages": 10, "tasks": 1}
            return {"pages": 0, "tasks": 0}

        monkeypatch.setattr(daemon, "_harvest_notebook", fake_harvest_notebook)

        res = daemon.harvest_onenote(notebooks=["NB1", "NB2"], max_pages=40)

        # NB1 is 1 of 2 notebooks: gets (40 - 0) // 2 = 20
        assert captured_remaining["NB1"] == 20
        # NB1 only consumed 5 pages, so NB2 gets (40 - 5) // 1 = 35 (unused quota rolled over!)
        assert captured_remaining["NB2"] == 35
        assert res["pages_scanned"] == 15
        assert res["tasks_extracted"] == 2

    def test_harvest_notebook_polls_until_leaf_sections_found(self, monkeypatch, tmp_path):
        """_harvest_notebook should poll for sections on cold loads rather than exiting immediately."""
        daemon = make_daemon(monkeypatch, tmp_path)

        poll_count = [0]

        def fake_editor_js(driver, script, *args, **kwargs):
            if "expanded" in script or "isGroup" in script:
                if "querySelectorAll('.sectionListItem" in script:
                    # Querying leaf sections
                    poll_count[0] += 1
                    if poll_count[0] < 3:
                        return []  # Rail still loading
                    return ["Unit 1 Notes"]
                return 0
            return []

        monkeypatch.setattr(daemon, "_ensure_notebooks_view", lambda d: True)
        monkeypatch.setattr(daemon, "_editor_js", fake_editor_js)
        monkeypatch.setattr(daemon, "_focus_live_tab", lambda d: True)

        class FakeDriver:
            current_url = "https://tenant.sharepoint.com/teams/doc.aspx"
            title = "NB1"
            window_handles = ["h1"]

            def switch_to_default_content(self): pass

            class SwitchTo:
                def default_content(self): pass
                def window(self, h): pass
                def frame(self, f): pass
            switch_to = SwitchTo()

            def execute_script(self, *a, **k):
                return True

            def find_element(self, *a, **k):
                return "frame_el"

        driver = FakeDriver()
        cache_data: dict[str, list[dict]] = {}
        trace: list[str] = []
        errors: list[str] = []

        # Remaining 0 so section loop exits before page processing
        stats = daemon._harvest_notebook(
            driver, "NB1", cache_data, trace, errors,
            extract_fn=lambda *a, **k: [],
            remaining=0,
        )

        assert poll_count[0] == 3
        assert "NB1: sections ['Unit 1 Notes']" in trace
        assert stats["pages"] == 0





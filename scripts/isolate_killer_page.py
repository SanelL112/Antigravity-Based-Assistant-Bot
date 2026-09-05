"""Isolate the OneNote page that kills the harvest session.

Runs its OWN Firefox against the daemon's profile — stop canvas-browser.service
first so the profile is free.  Walks to the AP Calculus notebook, finds the
page list, locates "New Seats", then navigates to the page after it and prints
the EXACT exception.  No relaunch anywhere; the only recovery is frame
re-anchoring, because OneNote's web app RECREATES the WebApplicationFrame
iframe on section/page clicks, which orphans the parked context and makes the
next execute_script throw "Browsing context has been discarded" even though
every tab is alive.
"""

import sys
import time
import traceback

from scripts.canvas_browser_daemon import BrowserDaemon, VirtualDisplay

NB_NAME = "AP Calculus AB 2026-2027"
ANCHOR = "new seats"  # substring, lowercase compare


def tb(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def alive(driver) -> bool:
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def dump_tabs(driver, label: str) -> None:
    """Print every surviving tab so we know WHAT was discarded."""
    try:
        handles = driver.window_handles
        print(f"[tabs:{label}] {len(handles)} handle(s) remain:", flush=True)
        for h in handles:
            try:
                driver.switch_to.window(h)
                print(f"    {driver.current_url[:100]!r} title={driver.title!r}",
                      flush=True)
            except Exception as exc:
                print(f"    <handle unreadable: {type(exc).__name__}: {exc}>",
                      flush=True)
    except Exception as exc:
        print(f"[tabs:{label}] window_handles itself threw: "
              f"{type(exc).__name__}: {exc}", flush=True)


def reanchor(driver) -> bool:
    """Re-enter the editor iframe after OneNote recreates it."""
    try:
        driver.switch_to.default_content()
        frame_el = driver.find_element("id", "WebApplicationFrame")
        driver.switch_to.frame(frame_el)
        return True
    except Exception as exc:
        print(f"[reanchor] failed: {type(exc).__name__}: {exc}", flush=True)
        return False


def js(driver, script, *args, tries: int = 4):
    """execute_script that re-anchors when the editor iframe is rebuilt."""
    last = None
    for attempt in range(tries):
        try:
            return driver.execute_script(script, *args)
        except Exception as exc:
            last = exc
            if "discarded" in str(exc) or "NoSuchWindow" in type(exc).__name__:
                print(f"[js] context discarded (attempt {attempt + 1}); "
                      f"re-anchoring", flush=True)
                if not reanchor(driver):
                    time.sleep(3)
                continue
            raise
    raise last


def main() -> int:
    display = VirtualDisplay()
    display.start()
    d = BrowserDaemon()
    d.start()
    time.sleep(2)
    driver = d.client.driver

    # 1. ClassLink -> Canvas (same chain the daemon uses on startup).
    try:
        d.client._sign_in_via_classlink()
        print("[auth] classlink chain completed", flush=True)
    except Exception as exc:
        print("[auth] classlink chain threw:", flush=True)
        print(tb(exc), flush=True)

    # 2. Reach the authenticated OneNote notebooks grid (daemon's own logic,
    #    including the stored-credential fallback for a dead M365 cookie).
    grid_ok = False
    try:
        grid_ok = d._ensure_notebooks_view(driver)
    except Exception as exc:
        print("[grid] _ensure_notebooks_view threw:", flush=True)
        print(tb(exc), flush=True)
    print(f"[grid] ok={grid_ok} url={driver.current_url[:90]!r}", flush=True)
    if not grid_ok:
        try:
            print("[signin] calling _microsoft_sign_in directly", flush=True)
            print("[signin] ->", d._microsoft_sign_in(), flush=True)
        except Exception as exc:
            print("[signin] threw:", flush=True)
            print(tb(exc), flush=True)
        try:
            grid_ok = d._ensure_notebooks_view(driver)
            print(f"[grid] retry ok={grid_ok}", flush=True)
        except Exception as exc:
            print("[grid] retry threw:", flush=True)
            print(tb(exc), flush=True)
    if not grid_ok:
        print("RESULT: could not reach OneNote grid — probe aborts (no relaunch).",
              flush=True)
        return 2
    if not alive(driver):
        print("RESULT: session died right after grid — probe aborts.", flush=True)
        return 3

    # 3. Open the notebook editor tab (replicating _harvest_notebook verbatim).
    clicked = False
    for _ in range(6):
        clicked = driver.execute_script(
            """
            const want = arguments[0].toLowerCase();
            const cands = Array.from(document.querySelectorAll('div, a'))
                .filter((el) => (el.textContent || '').trim().toLowerCase() === want);
            if (!cands.length) return false;
            cands[cands.length - 1].click();
            return true;
            """,
            NB_NAME,
        )
        if clicked:
            break
        time.sleep(2)
    if not clicked:
        print(f"RESULT: notebook tile {NB_NAME!r} not found on grid.", flush=True)
        return 4

    found_editor = False
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline and not found_editor:
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url.lower()
                title = (driver.title or "").lower()
            except Exception:
                continue
            if ("sharepoint.com" in url and "doc.aspx" in url) or NB_NAME.lower() in title:
                found_editor = True
                break
        if not found_editor:
            time.sleep(2)
    print(f"[editor] found={found_editor}", flush=True)
    if not found_editor:
        print("RESULT: editor tab never opened.", flush=True)
        return 5

    frame_el = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and frame_el is None:
        try:
            frame_el = driver.find_element("id", "WebApplicationFrame")
        except Exception:
            time.sleep(2)
    if frame_el is None:
        print("RESULT: WebApplicationFrame never appeared.", flush=True)
        return 6
    driver.switch_to.frame(frame_el)

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if js(driver, "return document.querySelectorAll('.sectionListItem').length;"):
            break
        time.sleep(3)

    sections = js(driver,
                  "return Array.from(document.querySelectorAll('.sectionListItem'))"
                  ".map(e => (e.innerText||'').trim()).filter(t => t.length > 1);"
                  ) or []
    print(f"[sections] {sections}", flush=True)

    # 4. Walk sections; every click goes through js() so a rebuilt iframe
    #    re-anchors instead of killing the probe.
    for sec in sections:
        print(f"\n[section] === {sec} ===", flush=True)
        try:
            hit = js(driver,
                     """
                     const want = arguments[0];
                     const els = Array.from(document.querySelectorAll('.sectionListItem'));
                     const s = els.find(e => (e.innerText||'').trim() === want);
                     if (s) { s.click(); return true; }
                     return false;
                     """,
                     sec)
            if not hit:
                print(f"[{sec}] section click failed", flush=True)
                continue
            time.sleep(3)
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if js(driver,
                      "return document.querySelectorAll('.pageListItem').length;"):
                    break
                time.sleep(3)

            pages = js(driver,
                       "return Array.from(document.querySelectorAll('.pageListItem'))"
                       ".map(e => (e.innerText||'').trim()).filter(t => t.length > 0);"
                       ) or []
            print(f"[{sec}] pages ({len(pages)}):", flush=True)
            for i, p in enumerate(pages):
                marker = "  <-- ANCHOR" if ANCHOR in p.lower() else ""
                print(f"  [{i:2d}] {p}{marker}", flush=True)

            idx = next(
                (i for i, p in enumerate(pages) if ANCHOR in p.lower()), None
            )
            if idx is None:
                print(f"[{sec}] no 'New Seats' page here; next section.", flush=True)
                continue

            # 5. THE ISOLATION: anchor page (control), the page after it
            #    (target), and two-after (post-check) — exact exceptions.
            for label, i in (
                ("CONTROL (re-click anchor page)", idx),
                ("TARGET (page after 'New Seats')", idx + 1),
            ):
                if i >= len(pages):
                    print(f"[{sec}] {label}: anchor is the LAST page — nothing after.",
                          flush=True)
                    continue
                pg = pages[i]
                print(f"\n===== {label}: {pg!r} =====", flush=True)
                try:
                    ok = js(driver,
                            """
                            const want = arguments[0];
                            const els = Array.from(document.querySelectorAll('.pageListItem'));
                            const p = els.find(e => (e.innerText||'').trim() === want);
                            if (p) { p.click(); return true; }
                            return false;
                            """,
                            pg)
                    print(f"click -> {ok}", flush=True)
                    time.sleep(6)
                    html = js(driver,
                              "const p = document.querySelector('#WACViewPanel');"
                              "return p ? p.outerHTML : '';")
                    print(f"panel html length: {len(html or '')}", flush=True)
                    print(f"title now: {driver.title!r}", flush=True)
                    if not html:
                        print("RESULT: panel never rendered for this page.", flush=True)
                except Exception as exc:
                    print(f"EXCEPTION while navigating to {pg!r}:", flush=True)
                    print(tb(exc), flush=True)
                print(f"session alive after: {alive(driver)}", flush=True)

            if idx + 2 < len(pages):
                nxt = pages[idx + 2]
                print(f"\n===== POST-CHECK (two pages later): {nxt!r} =====", flush=True)
                try:
                    ok = js(driver,
                            """
                            const want = arguments[0];
                            const els = Array.from(document.querySelectorAll('.pageListItem'));
                            const p = els.find(e => (e.innerText||'').trim() === want);
                            if (p) { p.click(); return true; }
                            return false;
                            """,
                            nxt)
                    time.sleep(6)
                    html = js(driver,
                              "const p = document.querySelector('#WACViewPanel');"
                              "return p ? p.outerHTML : '';")
                    print(f"click -> {ok}; panel html length: {len(html or '')}; "
                          f"alive={alive(driver)}", flush=True)
                except Exception as exc:
                    print("EXCEPTION on post-check:", flush=True)
                    print(tb(exc), flush=True)
            return 0
        except Exception as exc:
            print(f"[{sec}] section walk threw:", flush=True)
            print(tb(exc), flush=True)
            dump_tabs(driver, sec)
            if not alive(driver):
                print(f"RESULT: session died during section {sec!r} walk.", flush=True)
                return 7
    print("RESULT: no section with an anchor page was processed.", flush=True)
    return 8


if __name__ == "__main__":
    try:
        code = main()
    finally:
        try:
            d.close()
        except Exception:
            pass
    sys.exit(code)

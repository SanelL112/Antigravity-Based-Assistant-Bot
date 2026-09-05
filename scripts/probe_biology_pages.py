"""Deep probe: why does the page list never render for Class-Notebook sections?

Expands the groups, clicks ONE section with several click strategies, then
dumps every page-ish element/class and the page-panel HTML so we can see what
the walker's `.pageListItem` query is missing.  Own Firefox; stop
canvas-browser.service first.
"""

import sys
import time
import traceback

from scripts.canvas_browser_daemon import BrowserDaemon, VirtualDisplay

NB_NAME = "AP Biology Bleier 26-27"
SECTION = sys.argv[1] if len(sys.argv) > 1 else "U1 Chem of Life Class Notes"


def tb(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def focus_live_tab(driver) -> bool:
    try:
        handles = list(driver.window_handles)
    except Exception:
        return False
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            _ = driver.current_url
            return True
        except Exception:
            continue
    return False


def ensure_editor(driver) -> bool:
    try:
        if not focus_live_tab(driver):
            return False
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url.lower()
                title = (driver.title or "").lower()
            except Exception:
                continue
            if ("sharepoint.com" in url and "doc.aspx" in url) or NB_NAME.lower() in title:
                break
        driver.switch_to.default_content()
        frame_el = driver.find_element("id", "WebApplicationFrame")
        driver.switch_to.frame(frame_el)
        return True
    except Exception as exc:
        print(f"[ensure_editor] failed: {type(exc).__name__}: {exc}", flush=True)
        return False


def js(driver, script, *args, tries: int = 4):
    last = None
    for attempt in range(tries):
        try:
            return driver.execute_script(script, *args)
        except Exception as exc:
            last = exc
            if "discarded" in str(exc) or "NoSuchWindow" in type(exc).__name__:
                print(f"[js] discarded (attempt {attempt + 1}); re-anchoring", flush=True)
                if not ensure_editor(driver):
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

    try:
        d.client._sign_in_via_classlink()
    except Exception as exc:
        print("[auth] threw:", tb(exc), flush=True)
    ok = d._ensure_notebooks_view(driver)
    print(f"[grid] ok={ok}", flush=True)
    if not ok:
        try:
            d._microsoft_sign_in()
            for attempt in range(3):
                time.sleep(8)
                ok = d._ensure_notebooks_view(driver)
                if ok:
                    break
        except Exception as exc:
            print("[signin] threw:", tb(exc), flush=True)
    if not ok:
        print("RESULT: no grid", flush=True)
        return 2

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
        print("RESULT: notebook tile not found", flush=True)
        return 4

    found = False
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline and not found:
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url.lower()
                title = (driver.title or "").lower()
            except Exception:
                continue
            if ("sharepoint.com" in url and "doc.aspx" in url) or NB_NAME.lower() in title:
                found = True
                break
        if not found:
            time.sleep(2)
    if not found:
        print("RESULT: editor never opened", flush=True)
        return 5
    frame_el = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and frame_el is None:
        try:
            frame_el = driver.find_element("id", "WebApplicationFrame")
        except Exception:
            time.sleep(2)
    if frame_el is None:
        print("RESULT: no WebApplicationFrame", flush=True)
        return 6
    driver.switch_to.frame(frame_el)

    # Expand all collapsed groups.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        n = js(driver,
               """
               const els = Array.from(document.querySelectorAll(
                   '[aria-label*="Section Group"]'));
               let n = 0;
               for (const e of els) {
                 if (e.getAttribute('aria-expanded') === 'false') { e.click(); n++; }
               }
               return n;
               """) or 0
        if n == 0:
            break
        time.sleep(3)
    secs = js(driver,
              "return Array.from(document.querySelectorAll('.sectionListItem'))"
              ".map(e => (e.innerText||'').trim()).filter(t => t.length > 1);") or []
    print(f"[rail] sections after expand: {secs}", flush=True)

    print(f"\n[section] clicking {SECTION!r} three ways", flush=True)
    # Strategy A: native click on the matched element (what the walker does).
    a = js(driver,
           """
           const want = arguments[0];
           const els = Array.from(document.querySelectorAll('.sectionListItem'));
           const s = els.find(e => (e.innerText||'').trim() === want);
           if (!s) return 'not-found';
           s.click();
           return 'clicked:' + s.tagName + '.' + (s.className||'').toString().slice(0, 50);
           """, SECTION)
    print(f"[A native] {a}", flush=True)
    time.sleep(8)

    # Dump page-ish DOM after strategy A.
    dump = js(driver,
              """
              const clamp = (s, n) => (s || '').slice(0, n);
              const pageish = Array.from(document.querySelectorAll(
                  '[class*="ageList" i], [class*="ageTree" i], [role="treeitem"]'))
                .map(e => ({cls: clamp(e.className.toString(), 70),
                            text: clamp(e.innerText, 40)})).slice(0, 15);
              const sel = Array.from(document.querySelectorAll(
                  '[aria-selected="true"], [aria-current="true"]'))
                .map(e => clamp((e.innerText || e.getAttribute('aria-label') || ''), 50));
              return { pageListItems:
                         document.querySelectorAll('.pageListItem').length,
                       pageish, selected: sel,
                       panelHTML: clamp((document.querySelector(
                           '#PageListPanel, [id*="PageList"], [class*="ageList" i]') || {})
                           .outerHTML, 1800) };
              """) or {}
    print("[after A] pageListItem count:", dump.get("pageListItems"), flush=True)
    print("[after A] selected:", dump.get("selected"), flush=True)
    for item in (dump.get("pageish") or []):
        print(f"    pageish: {item}", flush=True)
    print("[after A] panelHTML:", flush=True)
    print(dump.get("panelHTML"), flush=True)

    # Strategy B: full mouse-event sequence on the element AND its children.
    b = js(driver,
           """
           const want = arguments[0];
           const els = Array.from(document.querySelectorAll('.sectionListItem'));
           const s = els.find(e => (e.innerText||'').trim() === want);
           if (!s) return 'not-found';
           const targets = [s, ...Array.from(s.querySelectorAll('*'))];
           const opts = {bubbles: true, cancelable: true, view: window};
           for (const t of targets) {
             t.dispatchEvent(new MouseEvent('mousedown', opts));
             t.dispatchEvent(new MouseEvent('mouseup', opts));
             t.dispatchEvent(new MouseEvent('click', opts));
           }
           return 'dispatched to ' + targets.length + ' node(s)';
           """, SECTION)
    print(f"[B events] {b}", flush=True)
    time.sleep(10)
    c1 = js(driver, "return document.querySelectorAll('.pageListItem').length;")
    print(f"[after B] pageListItem count={c1}", flush=True)

    # Strategy C: keyboard — focus the section item and press Enter/Space.
    c = js(driver,
           """
           const want = arguments[0];
           const els = Array.from(document.querySelectorAll('.sectionListItem'));
           const s = els.find(e => (e.innerText||'').trim() === want);
           if (!s) return 'not-found';
           s.focus();
           s.dispatchEvent(new KeyboardEvent('keydown',
             {key: 'Enter', code: 'Enter', bubbles: true, cancelable: true}));
           s.dispatchEvent(new KeyboardEvent('keyup',
             {key: 'Enter', code: 'Enter', bubbles: true, cancelable: true}));
           return 'enter dispatched; activeElement=' + (document.activeElement || {}).tagName;
           """, SECTION)
    print(f"[C keyboard] {c}", flush=True)
    time.sleep(10)
    c2 = js(driver, "return document.querySelectorAll('.pageListItem').length;")
    print(f"[after C] pageListItem count={c2}", flush=True)

    print("\nRESULT: probe complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

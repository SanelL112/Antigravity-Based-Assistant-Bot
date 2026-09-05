"""Probe: classify Biology's rail into leaf sections vs section groups.

Per diagnosis: items revealed by expanding a Class-Notebook group can
themselves be nested section groups (aria-expanded + expander chevron), which
have NO .pageListItem children — clicking one only toggles the tree.  This
probe walks the rail recursively:

  - group (aria-expanded / expander chevron): expand if collapsed, recurse;
  - leaf: click, then wait at most 10 s for .pageListItem (tight budget so a
    dead end fails fast instead of hanging the shell).

Runs its OWN Firefox against the daemon's profile — stop canvas-browser.service
first so the profile is free.  No relaunch logic anywhere.
"""

import sys
import time
import traceback

from scripts.canvas_browser_daemon import BrowserDaemon, VirtualDisplay

NB_NAME = "AP Biology Bleier 26-27"
PAGE_WAIT = 10          # hard cap waiting for a leaf's page list
GROUP_WAIT = 8          # budget for child items to appear after expanding


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


def classify(driver):
    """Return rail items with a leaf/group verdict for each.

    A group is anything with a 'Section Group' aria-label OR the hashed
    sectionGroup__* classes OR role="treeitem" with child containers/aria-expanded.
    """
    return js(driver,
              """
              const norm = (s) => (s || '').trim();
              const isGroup = (el) => {
                  if (!el) return false;
                  if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                  const label = (el.getAttribute('aria-label') || '').toLowerCase();
                  if (label.includes('section group')) return true;
                  const cls = (el.className || '').toString().toLowerCase();
                  if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                  if (el.getAttribute('role') === 'treeitem') {
                      if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                      const next = el.nextElementSibling;
                      if (next && next.getAttribute('role') === 'group') return true;
                  }
                  return false;
              };
              const els = Array.from(document.querySelectorAll(
                  '.sectionListItem, [role="treeitem"], [aria-label*="Section Group" i], '
                  + '[class*="sectionGroup__groupItemWrap"]'));
              const seen = new Set();
              const out = [];
              for (const e of els) {
                const isGroupEl = isGroup(e);
                const text = norm((e.querySelector('content') || {}).textContent
                                  || e.innerText || '');
                if (!text || text.length < 2) continue;
                const key = (isGroupEl ? 'G:' : 'L:') + text;
                if (seen.has(key)) continue;
                seen.add(key);
                out.push({ name: text, kind: isGroupEl ? 'group' : 'leaf',
                           expanded: e.getAttribute('aria-expanded'),
                           cls: (e.className || '').toString().slice(0, 70) });
              }
              return out;
              """) or []


def main() -> int:
    display = VirtualDisplay()
    display.start()
    d = BrowserDaemon()
    d.start()
    time.sleep(2)
    driver = d.client.driver

    try:
        d.client._sign_in_via_classlink()
        print("[auth] classlink chain completed", flush=True)
    except Exception as exc:
        print("[auth] threw:", flush=True)
        print(tb(exc), flush=True)

    ok = False
    try:
        ok = d._ensure_notebooks_view(driver)
    except Exception as exc:
        print("[grid] threw:", flush=True)
        print(tb(exc), flush=True)
    print(f"[grid] ok={ok}", flush=True)
    if not ok:
        try:
            print("[signin] ->", d._microsoft_sign_in(), flush=True)
            for attempt in range(3):
                time.sleep(8)
                ok = d._ensure_notebooks_view(driver)
                if ok:
                    break
        except Exception as exc:
            print("[signin/retry] threw:", flush=True)
            print(tb(exc), flush=True)
    if not ok:
        print("RESULT: could not reach OneNote grid.", flush=True)
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
        print(f"RESULT: notebook tile {NB_NAME!r} not found.", flush=True)
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

    # Cold SharePoint loads take >40s before the rail renders; wait for ANY
    # rail element (leaf sections and/or section groups) before interacting.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        n = js(driver,
               "return document.querySelectorAll('.sectionListItem, [role=\"treeitem\"], "
               "[aria-label*=\"Section Group\" i]').length;") or 0
        if n:
            print(f"[rail] {n} element(s) rendered", flush=True)
            break
        time.sleep(3)

    def expand_all_groups() -> int:
        """Click every collapsed group until none remain (rail is flat)."""
        total = 0
        for _ in range(6):
            did = js(driver,
                     """
                     const isGroup = (el) => {
                         if (!el) return false;
                         if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                         const label = (el.getAttribute('aria-label') || '').toLowerCase();
                         if (label.includes('section group')) return true;
                         const cls = (el.className || '').toString().toLowerCase();
                         if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                         if (el.getAttribute('role') === 'treeitem') {
                             if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                             const next = el.nextElementSibling;
                             if (next && next.getAttribute('role') === 'group') return true;
                         }
                         return false;
                     };
                     const els = Array.from(document.querySelectorAll(
                         '[role="treeitem"], .sectionListItem, [aria-label*="Section Group" i], '
                         + '[class*="sectionGroup__groupItemWrap"]'));
                     let n = 0;
                     const seen = new Set();
                     for (const e of els) {
                       if (!isGroup(e)) continue;
                       if (seen.has(e)) continue;
                       seen.add(e);
                       if (e.getAttribute('aria-expanded') === 'false') {
                         const target = e.querySelector('[class*="chevron" i], [class*="expander" i], [data-icon-name*="Chevron" i], [aria-expanded]') || e;
                         target.click();
                         n++;
                       }
                     }
                     return n;
                     """) or 0
            total += did
            print(f"[expand] clicked {did} collapsed group(s)", flush=True)
            if not did:
                break
            time.sleep(3)
        return total

    expand_all_groups()

    items = classify(driver)
    print("\n========== FINAL RAIL ==========", flush=True)
    for it in items:
        print(f"  [{it['kind']}] {it['name']!r} expanded={it['expanded']} "
              f"cls={it['cls'][:50]}", flush=True)
    print("========== END FINAL RAIL ==========", flush=True)

    leaves = [it for it in items if it["kind"] == "leaf"]
    for it in leaves:
        hit = js(driver,
                 """
                 const want = arguments[0];
                 const isGroup = (el) => {
                     if (!el) return false;
                     if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                     const label = (el.getAttribute('aria-label') || '').toLowerCase();
                     if (label.includes('section group')) return true;
                     const cls = (el.className || '').toString().toLowerCase();
                     if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                     if (el.getAttribute('role') === 'treeitem') {
                         if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                         const next = el.nextElementSibling;
                         if (next && next.getAttribute('role') === 'group') return true;
                     }
                     return false;
                 };
                 const els = Array.from(document.querySelectorAll('.sectionListItem, [role="treeitem"]'));
                 const s = els.find(e => !isGroup(e) && (((e.querySelector('content') || {}).textContent || e.innerText || '').trim() === want));
                 if (s) { s.click(); return true; }
                 return false;
                 """, it["name"])
        deadline = time.monotonic() + PAGE_WAIT
        count = 0
        while time.monotonic() < deadline:
            count = js(driver,
                       "return document.querySelectorAll('.pageListItem').length;") or 0
            if count:
                break
            time.sleep(2)
        pages = js(driver,
                   "return Array.from(document.querySelectorAll('.pageListItem'))"
                   ".map(e => (e.innerText||'').trim()).filter(t => t.length > 0);"
                   ) or []
        print(f"[leaf] {it['name']!r} click={hit} pageListItems={count} "
              f"named={len(pages)}", flush=True)
        for p in pages[:8]:
            print(f"    page: {p}", flush=True)

    print("\nRESULT: probe complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

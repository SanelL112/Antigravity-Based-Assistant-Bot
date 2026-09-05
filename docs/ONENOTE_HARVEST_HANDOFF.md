# OneNote Harvest / Canvas Browser Bug-Audit Handoff

**Prepared:** 2026-09-05  
**Repository:** `personal-assistant-bot`  
**Branch:** `fix/2026-07-bug-audit`  
**Primary daemon:** `scripts/canvas_browser_daemon.py`  
**Audience:** A new coding agent continuing the investigation

> This document is a handoff, not a claim that the system is currently healthy. Historical production verification was successful for the iframe-resilience work, but the daemon is currently down in an `Xvfb` startup loop. Read the **Current state** and **Next actions** sections first.

---

## 1. Original problem

The OneNote harvest endpoint (`/onenote/harvest`) was intermittently stopping partway through a notebook walk. Symptoms included:

- Selenium errors such as:

  ```text
  selenium.common.exceptions.NoSuchWindowException: Browsing context has been discarded
  ```

- The daemon treating recoverable browser/editor problems as dead Firefox sessions.
- Partial harvests being lost or replacing a good cache with an empty cache.
- The HTTP client timing out while the server-side harvest continued, causing misleading `BrokenPipeError` messages when the daemon later tried to send the response.
- AP Biology appearing to have `sections []` and contributing no pages/tasks.

The investigation also considered a suspected “killer page” immediately after the AP Calculus page `New Seats!`, Firefox memory pressure, expired Microsoft authentication, stale tabs, and OneNote Class Notebook structure.

---

## 2. Verified root cause: stale OneNote iframe context

The main Calculus/Stat failure was **not** a killer page, OOM kill, or necessarily a dead Firefox process.

OneNote’s SharePoint editor uses an iframe with id `WebApplicationFrame`. After a section or page click, the web app can recreate that iframe. Selenium remains logically parked in the old iframe context. The next `execute_script`/frame operation then raises `Browsing context has been discarded`, even though the browser tabs themselves remain alive.

Evidence gathered:

- Raw journal traceback showed the exception at `_ensure_notebooks_view`, specifically around `driver.switch_to.default_content()`, before the page walk had started in that run.
- A tab dump taken after a discard showed all relevant tabs still alive, including ClassLink, OneNote, and the SharePoint editor.
- `dmesg -T | grep -iE "oom|killed process|firefox"` returned no OOM or Firefox-kill evidence.
- The standalone Calculus isolation probe navigated from `New Seats!` to the next page (`Untitled Page`) successfully; the page rendered and the session remained alive.
- The apparent failure location moved between runs, consistent with an iframe-recreation race rather than one deterministic page.

### Implemented iframe fix

`BrowserDaemon._editor_js()` now retries editor JavaScript calls. On discard/no-browsing-context errors it:

1. Re-enters default content.
2. Finds `#WebApplicationFrame` again.
3. Switches into the newly created iframe.
4. Retries, up to four attempts.

This helper is used for section/page clicks, section/page-list reads, page HTML extraction, and related editor operations. `_reanchor_editor()` and `_focus_live_tab()` support the recovery.

This was live-verified historically: the harvest walked through Calculus and into Stat without the previous discard storm, retaining pages through the end of the Stat walk.

---

## 3. Other daemon fixes already implemented

All of the following are in `scripts/canvas_browser_daemon.py` unless noted otherwise.

### Harvest retry/self-healing

- Removed the unreachable retry logic caused by duplicate `except Exception` clauses on the same `try` block.
- Added per-notebook failure isolation so one notebook (for example, Biology) does not abort all remaining notebooks.
- Added `_recover_harvest_session()` with explicit outcomes: `alive`, `relaunched`, or `dead`.
- After relaunch, `_wait_for_grid()` waits for authentication/grid recovery before retrying instead of immediately spending attempts on a dead browser.
- Recovery can run the stored Microsoft credential flow via `_microsoft_sign_in()` when silent SSO is insufficient.

### Cache safety and partial progress

- A harvest that discovers zero new pages no longer overwrites a populated cache with `{}`.
- Partial `cache_data` is merged into the previous cache after an interrupted walk.
- A re-extracted page overwrites its own stale entry while unrelated existing entries survive.
- Cross-run resume tracks previously harvested page titles and skips them, allowing a later run to continue deeper into a notebook instead of repeatedly dying at the same pages.
- Diagnostic harvest trace messages are now forwarded to the journal through `logger.info`, not only returned in the HTTP response. This matters because a timed-out client loses the response body.

### RAG/page retention

Harvested reading-order page text is retained under:

```text
source_cache/onenote_pages/<notebook>/<section>/<page>.md
```

The embedding indexer can consume this recursively. Ink-only pages may still need the separate vision/transcription pipeline.

### Existing OneNote integrations

- `scrapers/onenote_alerts.py` provides once-per-task new-task alerts using `cache/onenote_seen_tasks.json`.
- `main.py` sends the OneNote alert output through the existing Telegram update path.
- `ai_processor.assemble_digest` includes a “From your notebooks” section using new pages and upcoming OneNote items.
- `cache/onenote_page_extractions.json` remains the downstream task cache.

---

## 4. AP Biology: confirmed Class Notebook structure

AP Biology (`AP Biology Bleier 26-27`) is not a plain notebook.

The standalone probe confirmed:

- There are zero usable top-level leaf sections initially.
- The rail contains collapsed section groups, including `_Content Library` and `Lathiya, Sanel`.
- Expanding the groups reveals Biology content such as `Common reference sheets`, `U1 Chem of Life Class Notes`, and `U2 Cells and Transport`.
- The daemon’s initial plain `.sectionListItem` query therefore returned an empty list before the group expansion change.

### Implemented Biology change in the daemon

`_harvest_notebook()` now clicks collapsed elements matching:

```css
[aria-label*="Section Group"]
```

It then waits for the rail to re-render and enumerates `.sectionListItem` again. The change is harmless for Calc/Stat because those notebooks have no matching groups.

Journal logging was added around this path. A successful Biology run should contain messages like:

```text
OneNote harvest: AP Biology Bleier 26-27: expanded 2 section group(s)
OneNote harvest: AP Biology Bleier 26-27: sections [...]
```

### Important remaining Biology issue

The newly exposed Biology items include a nested section group such as:

```text
U2 Cells and Transport Extra Resources
```

This is a **section group**, not a leaf section. It has no `.pageListItem` children. Clicking it toggles `aria-expanded` and reveals nested leaf sections in the sidebar. The current daemon still treats all `.sectionListItem` values as directly clickable leaf sections and waits up to 40 seconds for `.pageListItem`. That explains the observed pattern:

- Groups expanded successfully.
- Sections were listed successfully.
- Biology then spent roughly ten minutes with zero pages because group items were mistaken for leaf sections.

This nested-group handling is **not finished**.

---

## 5. Probe/diagnostic scripts

These are untracked investigation artifacts currently in the repository:

- `scripts/isolate_killer_page.py`
  - Opens AP Calculus in its own Firefox.
  - Tests the `New Seats!` page and the following page.
  - Contains local iframe re-anchoring, but no daemon relaunch logic.
  - Historical result: the page after `New Seats!` was healthy.

- `scripts/probe_biology_notebook.py`
  - Intended to classify Biology rail entries as leaf sections vs section groups.
  - Expands groups and only waits for `.pageListItem` on leaves.
  - Has a 10-second leaf page-list timeout in the current source.
  - Current source still needs cleanup/verification: it contains duplicate cold-load rail waits and has gone through several iterative rewrites.

- `scripts/probe_biology_pages.py`
  - Earlier exploratory probe used to inspect why Biology page lists were empty.
  - It is less authoritative than the newer `probe_biology_notebook.py`.

### Probe constraints

Before running a standalone probe, stop the daemon so Firefox’s profile is not locked. Clean up orphaned processes safely; avoid a `pkill -f` pattern that matches the shell command itself. The earlier investigation accidentally killed its own shell several times with patterns containing literal `Xvfb`/`probe_biology` text.

Use self-excluding patterns, for example:

```bash
pkill -9 -f '[p]robe_biology' || true
pkill -9 -f '[f]irefox' || true
pkill -9 -f '[X]vfb' || true
```

Run probes synchronously when possible; background processes did not reliably survive between agent tool calls.

---

## 6. Tests and historical verification

### Tests added

- `tests/test_harvest_resilience.py`
  - Retry path is reachable.
  - Relaunched driver is used on retry.
  - Partial gains survive a transient failure.
  - Existing cache entries survive partial writes.
  - Empty harvests do not wipe a good cache.
  - Successful harvests merge with prior cache.
  - Re-extracted pages replace their own stale values.
  - Cross-run title skipping works.
  - Session recovery outcomes are covered.

- `tests/test_onenote_alerts.py`
  - Covers the OneNote alert/retention behavior added in the same work.

Historical results:

- Targeted resilience/alert tests passed.
- Full suite reached **270 passing tests** with one known pre-existing failure in topic discovery’s online-refine path. Do not attribute that failure to the browser-daemon changes without reproducing it independently.
- `py_compile` passed for the daemon and the probes at the relevant checkpoints.

Before declaring new work complete, run:

```bash
venv/bin/python -m py_compile scripts/canvas_browser_daemon.py scripts/probe_biology_notebook.py
venv/bin/python -m pytest tests/test_harvest_resilience.py tests/test_onenote_alerts.py -q
venv/bin/python -m pytest tests/ -q
```

The full suite may still contain the unrelated topic-discovery failure noted above.

---

## 7. Historical production results

The iframe-resilience and cache-safety changes were exercised against the live daemon during the investigation.

One clean long harvest historically showed:

- Calculus and Stat walked end-to-end.
- Cache grew from 30 to 72 entries at one checkpoint.
- 80 real dated tasks were extracted at that checkpoint.
- 72 markdown pages were retained for RAG.
- A later scheduled run grew the cache to 172 and then another run to 194 as new Stat content was found.
- Cross-run resume caused already-cached Calculus pages to be skipped.
- Client-side curl timeouts caused `BrokenPipeError` on response delivery, but did not mean the server-side harvest failed; journal retention and cache timestamps were used to distinguish this.

AP Biology did **not** successfully contribute pages in those runs. The later journal trace proved that top-level group expansion worked, but nested group items were still being treated as leaf sections. Biology therefore remains the outstanding functional verification target.

Do not describe the current daemon as production-healthy solely from these historical results.

---

## 8. Current operational state at handoff

At handoff time, `canvas-browser.service` is **not running successfully**.

Current journal pattern:

```text
RuntimeError: Could not start the Canvas virtual display.
canvas-browser.service: Main process exited with status=1/FAILURE
```

Systemd is repeatedly restarting the service. The likely immediate cause is an orphaned display server:

```text
/usr/bin/Xvfb :99 -screen 0 1440x900x24 -nolisten tcp
```

The service’s `VirtualDisplay.start()` tries to start another `Xvfb :99`, sees that its child exits immediately, and raises. This is an operational/profile cleanup issue, separate from the OneNote parser logic. No Firefox process or OOM kill was present in the latest process/OOM check.

Do not start a new probe until the profile/display ownership is clear. First inspect the existing Xvfb process and service configuration, then cleanly stop the stale process or use the intended display ownership. Avoid broad process kills unless necessary.

Also note: the earlier investigation enabled a global passwordless sudoers entry and left a questionable `SUDO_PASSWORD` setting in `.env`. These are security/housekeeping issues; do not print secrets or commit `.env` contents. Review and remove the global `NOPASSWD: ALL` rule if it is no longer intentionally required.

---

## 9. Recommended next actions

### A. Restore the daemon safely

1. Inspect the service unit and current display ownership:

   ```bash
   systemctl cat canvas-browser.service
   ps -ef | grep -E '[X]vfb|[f]irefox'
   systemctl status canvas-browser.service --no-pager
   ```

2. Determine whether the existing `Xvfb :99` belongs to the daemon, a probe, or an orphan.
3. Stop/remove only the stale owner, then restart the service.
4. Verify `/health` and journal authentication before triggering a harvest.

### B. Finish the Biology parser/probe

Implement a shared, explicit leaf/group classifier rather than more ad hoc `dispatchEvent` hacks:

- Group indicators may include:
  - `aria-expanded` present;
  - `aria-label` containing `Section Group`;
  - known section-group wrapper classes such as `sectionGroup__groupItemWrap`;
  - a child expander/chevron/treeitem wrapper.
- Expand collapsed groups (`aria-expanded="false"`) and wait for the rail to re-render.
- Recursively or iteratively discover nested child sections.
- Only click a leaf section and wait for `.pageListItem` after confirming it is a leaf.
- Use a hard 10-second wait for leaf page-list population in the diagnostic probe. Consider a shorter/configurable timeout in the production walker so a structural mismatch fails quickly and is logged.
- Preserve the actual section path/group path in cache keys; do not collapse distinct nested sections solely by title.
- Add hermetic tests for classification and nested-group traversal where possible.

### C. Verify Biology end-to-end

After the daemon is healthy:

1. Run the focused Biology probe synchronously with the daemon stopped.
2. Confirm output distinguishes the nested `U2 ... Extra Resources` group from leaves.
3. Confirm child leaf sections produce nonzero `.pageListItem` counts.
4. Restart the daemon.
5. Trigger a focused harvest, preferably with `notebooks=AP Biology Bleier 26-27` and a conservative page budget.
6. Inspect the journal, response, cache, and `source_cache/onenote_pages/`.
7. Verify Biology has real cache entries and no silent `sections []`/zero-page result.

### D. Improve production observability

- Preserve the harvest result server-side or in a bounded diagnostic log so client curl timeouts do not lose the only trace.
- Keep the journal summary per notebook: groups expanded, sections discovered, pages scanned, tasks extracted, errors, and cache-write result.
- Treat `BrokenPipeError` while sending an already-completed HTTP response as client disconnect noise, not as a harvest failure.
- Consider a separate asynchronous harvest job/status endpoint rather than holding one HTTP request open for 10+ minutes.

---

## 10. Files changed or added by the investigation

Relevant files:

```text
docs/ONENOTE_CONTEXT.md
scripts/canvas_browser_daemon.py
scripts/isolate_killer_page.py
scripts/probe_biology_notebook.py
scripts/probe_biology_pages.py
scrapers/onenote_alerts.py
tests/test_harvest_resilience.py
tests/test_onenote_alerts.py
```

The working tree also contains many unrelated generated/academic-note modifications. A future agent must not stage or revert those indiscriminately. Before committing, inspect the diff and stage only files directly related to the intended change.

---

## Bottom line

The original Calculus/Stat harvest failure was caused by stale Selenium context after OneNote rebuilt its editor iframe, and that part has a working re-anchor/retry fix with historical live verification. Cache preservation, partial merge, cross-run resume, per-notebook isolation, authentication recovery, RAG retention, and journal trace forwarding are also implemented and tested.

The remaining functional bug is AP Biology’s nested Class Notebook structure: a nested section group is still being mistaken for a leaf section. The immediate operational blocker is separate: the daemon currently cannot start because an orphaned `Xvfb :99` prevents `VirtualDisplay.start()` from succeeding.

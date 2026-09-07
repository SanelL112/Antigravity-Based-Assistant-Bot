# OneNote Harvest Bug Audit

> **Audience:** Future coding agents and maintainers  
> **Scope:** OneNote browser harvesting, cache persistence, scheduled execution, and the supporting Canvas/Firefox daemon  
> **Primary implementation:** `scripts/canvas_browser_daemon.py`  
> **Related documents:** [`ONENOTE_CONTEXT.md`](ONENOTE_CONTEXT.md), [`ONENOTE_HARVEST_HANDOFF.md`](ONENOTE_HARVEST_HANDOFF.md)  
> **Investigation period:** September 2026

## 1. Executive summary

The OneNote harvester originally failed in several different layers. The failures looked similar from the outside—harvests stopped early, returned zero pages, or reported a dead browser—but they had different causes:

1. OneNote repeatedly rebuilt its editor iframe, leaving Selenium in a discarded browsing context.
2. Class Notebook section groups were collapsed and were not included by the plain-notebook section selector.
3. After groups were expanded, group headers were mistaken for leaf sections.
4. Biology's Office/Fabric tree required a full mouse activation sequence beginning with `mousedown`; a bare Selenium `.click()` could return successfully without selecting anything.
5. The scheduled systemd harvest raced the daemon startup and attempted HTTP access before the daemon's port was ready.
6. Recovery logic, cache persistence, observability, and page-budget handling allowed transient failures to become data loss or silent no-op runs.
7. Operational issues—an orphaned Xvfb display and a memory-hungry Cline process—made browser failures appear more severe than the application bugs themselves.

The final live verification demonstrated that the core harvesting path works after the fixes:

```text
AP Biology Bleier 26-27: 101 pages, 159 tasks
```

The persisted cache grew from 194 entries with no Biology pages to 580 entries, including 115 Biology entries. The daemon was subsequently confirmed active and authenticated, and the scheduled timer was active for the next run.

This document distinguishes confirmed bugs from ruled-out hypotheses. Do not re-investigate the “killer page” or Firefox OOM theory without new evidence.

---

## 2. System architecture

The relevant execution path is:

```text
onenote-harvest.timer
        |
        v
onenote-harvest.service
        |  curl http://127.0.0.1:8976/onenote/harvest?... 
        v
canvas-browser.service
        |
        v
scripts/canvas_browser_daemon.py
        |
        +-- Xvfb virtual display :99
        +-- Firefox + geckodriver
        +-- ClassLink -> ADFS -> Canvas authentication
        +-- M365/OneNote navigation
        +-- Selenium section/page traversal
        +-- task extraction
        |
        +-- cache/onenote_page_extractions.json
        +-- source_cache/onenote_pages/*.md
```

### Important paths and services

| Component | Location or unit | Purpose |
|---|---|---|
| Browser daemon | `scripts/canvas_browser_daemon.py` | Maintains a logged-in Firefox session and exposes the harvest HTTP endpoint |
| Browser service | `canvas-browser.service` | Runs the daemon under systemd |
| Harvest service | `onenote-harvest.service` | Runs the HTTP harvest request as a oneshot service |
| Harvest timer | `onenote-harvest.timer` | Starts the harvest around 02:00 ET with a randomized delay |
| Structured cache | `cache/onenote_page_extractions.json` | Dictionary keyed by `Notebook/Section/Page` path, with extracted tasks as values |
| RAG page cache | `source_cache/onenote_pages/` | Retained page text/markdown for search and embeddings |
| Resilience tests | `tests/test_harvest_resilience.py` | Tests cache, retry, partial-result, and browser-harvest resilience |
| Alert tests | `tests/test_onenote_alerts.py` | Tests newly-seen OneNote task alert behavior |

### Relevant daemon locations

Line numbers can move; use function names as the stable reference.

- `restart_browser()` — approximately line 125
- `auto_reauthenticate()` — approximately line 256
- `_microsoft_sign_in()` — approximately line 433
- `harvest_onenote()` — approximately line 849
- `_wait_for_grid()` — approximately line 1038
- `_focus_live_tab()` — approximately line 1109
- `_reanchor_editor()` — approximately line 1125
- `_editor_js()` — approximately line 1135
- `_ensure_notebooks_view()` — approximately line 1153
- `_harvest_notebook()` — approximately line 1242
- Class Notebook group expansion — approximately lines 1323–1370
- Fabric section activation — approximately lines 1447–1455
- keyboard activation fallback — approximately lines 1475–1482

---

## 3. Confirmed bugs

## BUG-01 — Stale `WebApplicationFrame` browsing context

**Layer:** Selenium/browser integration  
**Severity:** Critical for harvesting  
**Status:** Fixed

### What it was

The OneNote web application uses an editor iframe commonly identified as `WebApplicationFrame`. OneNote replaces or recreates this iframe after section and page navigation. Selenium remained attached to the old frame after the replacement.

The browser tabs themselves remained alive, but the driver's current browsing context pointed at an orphaned iframe.

### Observable symptoms

The daemon reported exceptions such as:

```text
selenium.common.exceptions.NoSuchWindowException:
Message: Browsing context has been discarded
```

The most useful traceback placed the failure at:

```text
driver.switch_to.default_content()
```

inside `_ensure_notebooks_view()`.

Failures occurred at different sections or pages on different runs. That variability initially made the issue look like a bad page, a browser crash, or memory exhaustion.

### Program impact

- The harvest could stop before completing the notebook walk.
- Recovery code treated a healthy browser as a dead session.
- Partial results could be lost if the failure happened before persistence.
- The same page could work on one run and fail on another because the race depended on when the iframe was rebuilt relative to the next Selenium command.

### Evidence

A tab dump taken immediately after the exception showed all relevant tabs alive, including:

```text
myapps.classlink.com/home
onenote.cloud.microsoft/notebooks
forsythk12org-my.sharepoint.com/.../doc2.aspx
```

The browser was not killed by the kernel, and the failure occurred around iframe context handling rather than page content processing.

### Fix

The daemon now uses `_editor_js()` as the common wrapper for editor JavaScript. It re-anchors the driver to a live editor tab and re-enters the current `WebApplicationFrame` when a discarded-context failure occurs. It retries several times instead of immediately declaring the entire browser session dead.

The re-anchor helpers are:

- `_focus_live_tab()` — searches for a usable editor tab.
- `_reanchor_editor()` — restores the correct top-level document and iframe.
- `_editor_js()` — executes editor JavaScript with retry/re-anchor behavior.

### Verification

After this fix, a live harvest walked Calculus through Stat end-to-end without the previous discard storm. It retained 72 pages during the first major clean run and later continued through Biology and Stat overnight.

---

## BUG-02 — Class Notebook section groups were invisible to the section walker

**Layer:** OneNote DOM traversal  
**Severity:** Critical for AP Biology  
**Status:** Fixed

### What it was

AP Biology is a OneNote Class Notebook rather than a plain notebook. Its sections are nested inside collapsed section groups such as:

- `_Content Library`
- `Lathiya, Sanel`

The original walker queried ordinary `.sectionListItem` elements at the top level. Because the groups were collapsed, the actual child sections were not present in the visible/queryable section list.

### Observable symptoms

The notebook appeared in the notebook list, but section enumeration returned:

```text
AP Biology Bleier 26-27: sections []
```

No exception was raised, so the harvest could report a clean-looking result while silently walking zero Biology sections.

### Program impact

- Biology contributed zero pages and zero tasks.
- The per-notebook isolation logic did not classify it as a failure because there was no thrown exception.
- Cross-run resume could not help: there were no Biology page keys in the cache to resume from.
- The final assignment calendar and RAG index lacked Biology content.

### Evidence

A standalone DOM probe found zero top-level section items but two collapsed section groups. Expanding the groups revealed actual sections, including:

```text
Common reference sheets
U1 Chem of Life Class Notes
U1 Chem of Life Extra Resources
U2 Cells and Transport Class Notes
U2 Cells and Transport Extra Resources
U1 Chemistry of Life
U2 Cells and Transport
U3 Metabolic Pathways
U4 Signaling Pathways
U5 Heredity
U6 Molecular Genetics
U7 Evolution
U8 Ecology
```

### Fix

`_harvest_notebook()` now detects and expands collapsed section groups before enumerating leaves. The implementation checks attributes/classes associated with groups, including `aria-expanded`, group-related classes, and child-container indicators. It records the expansion count in both the response trace and the daemon journal.

The live diagnostic line was:

```text
AP Biology Bleier 26-27: expanded 10 section group(s)
```

The implementation is intentionally harmless for plain notebooks: Calculus and Stat have no section groups, so there is nothing to expand.

### Verification

After deployment, Biology enumerated all 13 visible leaf sections instead of returning an empty list. The final overnight run harvested 101 Biology pages and 159 tasks.

---

## BUG-03 — Section groups were treated as leaf sections

**Layer:** OneNote DOM classification  
**Severity:** High for Class Notebooks  
**Status:** Fixed

### What it was

Expanding the top-level groups exposed nested objects that were a mixture of:

- Actual leaf sections, which load a page list when selected.
- Nested section groups, which only expand/collapse the sidebar tree.

The original logic treated all discovered section-like elements as selectable sections.

For example, `U2 Cells and Transport Extra Resources` was identified during investigation as a section group rather than a regular leaf section.

### Observable symptoms

Clicking a group changed `aria-expanded` but did not create `.pageListItem` children. The walker then waited for pages that could never appear.

Earlier runs therefore spent approximately 40 seconds per mistaken item waiting for a page list. A 13-item Biology walk could spend about ten minutes and still return:

```text
AP Biology Bleier 26-27: 0 pages, 0 tasks
```

### Program impact

- Time was wasted waiting on non-leaf nodes.
- Valid child sections were skipped.
- The run looked like a slow or broken page-list load rather than a tree traversal error.
- A notebook could be technically “successful” from the daemon's perspective while producing no data.

### Fix

The section discovery code now distinguishes groups from leaves using DOM signals such as:

- `aria-expanded`
- group-related class names such as `sectionGroup` and `groupItemWrap`
- group/child-container descendants
- treeitem/group relationships

Only leaf names are returned for the page-walking loop. Groups are expanded first, then their children are reconsidered.

### Verification

The live Biology trace showed 10 groups expanded and 13 leaf sections enumerated. The final page walk included pages under the nested `U2 Cells and Transport Extra Resources` group.

---

## BUG-04 — Bare `.click()` did not activate Class Notebook Fabric sections

**Layer:** OneNote Office/Fabric UI interaction  
**Severity:** Critical for Biology pages  
**Status:** Fixed

### What it was

The Class Notebook sidebar uses an Office/Fabric tree. A Selenium `.click()` on a matching element could return successfully without causing the application to select the section.

The browser automation interpreted the command as successful because no Selenium exception occurred. OneNote's application state, however, remained on the previous selection.

The working interaction required a full mouse event sequence beginning with `mousedown`.

### Observable symptoms

The isolation probe tested three approaches on `U1 Chem of Life Class Notes`:

| Strategy | Result |
|---|---|
| Native Selenium `.click()` | `pageListItem count: 0`; selected item remained `Home` |
| JS `mousedown` + `mouseup` + `click` dispatch | `pageListItem count: 73` |
| Keyboard Enter event | `pageListItem count: 73` |

The native click therefore looked successful to Selenium but did not select anything in the React/Fabric application.

### Program impact

- Every Biology section could be “clicked” without loading its pages.
- The walker consistently returned zero pages without an exception.
- The 10-second page-list timeout made the failure faster, but did not solve the underlying selection problem.
- Because the failure was silent, it was initially confused with a selector or page-list rendering problem.

### DOM details

The Biology rail contains Fabric-style elements such as:

```text
navItem ... sectionItem
```

and group wrappers such as:

```text
sectionGroup__groupItemWrap...
```

This differs from the simpler plain-notebook DOM. A selector can find a text-bearing element that is not the node/event target OneNote uses for selection.

### Fix

The daemon now activates section elements by dispatching the complete event sequence to the matched node and its descendants:

```javascript
const targets = [hit, ...Array.from(hit.querySelectorAll('*'))];
const opts = {bubbles: true, cancelable: true, view: window};
for (const t of targets) {
    t.dispatchEvent(new MouseEvent('mousedown', opts));
    t.dispatchEvent(new MouseEvent('mouseup', opts));
    t.dispatchEvent(new MouseEvent('click', opts));
}
```

If the page list is still empty after the initial wait, the daemon sends keyboard Enter events as a fallback.

Page items use the same robust activation pattern rather than relying on a bare `.click()`.

### Verification

After deployment, the next successful run traversed Biology pages and logged:

```text
AP Biology Bleier 26-27: 101 pages, 159 tasks
```

This is the strongest proof that the group expansion and leaf activation fixes work together.

---

## BUG-05 — Self-heal/retry branch was unreachable

**Layer:** Python exception handling  
**Severity:** High  
**Status:** Fixed

### What it was

The daemon had two `except Exception` clauses associated with the same `try` block. Python enters the first matching handler, so the later generic handler containing retry/relaunch behavior could never execute.

### Program impact

- Browser/session failures were caught by the first handler.
- The intended relaunch and retry logic was skipped.
- A transient failure could terminate a harvest rather than recover.
- Operators saw a session-dead warning without the expected self-healing behavior.

### Fix

Exception handling was split so that specific transient browser/session failures reach the recovery path, while non-recoverable errors are reported separately. The recovery path now includes browser relaunch, re-anchoring, authentication waiting, and per-notebook continuation where appropriate.

### Verification

During live runs, the daemon detected browser deaths, relaunched Firefox, and continued rather than abandoning the whole harvest. The iframe re-anchor logic also prevented healthy tabs from being misclassified as dead sessions.

---

## BUG-06 — Empty harvest could wipe good cache data

**Layer:** Persistence/data safety  
**Severity:** Critical for downstream data  
**Status:** Fixed

### What it was

A harvest that returned zero pages could overwrite the persisted OneNote cache with an empty result. Empty results were possible from authentication failures, DOM timing failures, section misclassification, or a dead browser.

### Program impact

- Previously harvested pages disappeared from the cache.
- Assignment extraction and RAG search lost historical content.
- A transient browser problem became permanent data loss until a later successful run rebuilt the cache.

### Fix

`harvest_onenote()` now treats a zero-page result as unsafe to write. It preserves the previous cache and records a diagnostic message:

```text
harvest produced 0 pages; keeping the previous cache intact
```

The HTTP response also reports:

```text
harvest produced 0 pages; kept last-known-good cache
```

### Verification

Multiple zero-page runs were observed during the investigation. The cache remained intact rather than being wiped. A later successful run merged new pages into the existing data.

---

## BUG-07 — Partial harvest results could be discarded

**Layer:** Persistence/recovery  
**Severity:** High  
**Status:** Fixed

### What it was

If a browser session died after several notebooks or pages had already been harvested, the partial in-memory result could be discarded when the run failed.

### Program impact

- Long walks had all-or-nothing persistence behavior.
- A failure near the end of a multi-hour run wasted all earlier work.
- Repeated retries revisited pages unnecessarily and increased browser load.

### Fix

The daemon retains the previous known-good cache, overlays partial `cache_data`, and writes the merged dictionary when a run has made useful progress:

```python
merged = dict(previous_cache) if good_before else {}
merged.update(cache_data)
cache_path.write_text(json.dumps(merged, indent=1), encoding="utf-8")
```

The run also keeps partial page files in `source_cache/onenote_pages/` as they are processed.

### Verification

A mid-harvest browser death retained pages discovered before the failure. The cache grew from 30 to 32 entries rather than losing the original 30. Later runs continued into previously unharvested territory.

---

## BUG-08 — Cross-run resume was missing or insufficient

**Layer:** Harvest scheduling/performance  
**Severity:** High for long notebooks  
**Status:** Fixed

### What it was

Without a persisted set of previously seen page titles, every retry started from the beginning. A long notebook walk could repeatedly spend its entire budget on pages already processed.

### Program impact

- Browser time was wasted reprocessing known pages.
- A retry after a mid-walk failure might never reach Biology or Stat.
- The fixed page budget was consumed before new content was found.

### Fix

At harvest start, page titles are derived from existing cache keys and used as `seen_titles`. During a retry or subsequent run, known titles are skipped while new pages are retained.

Relevant logic is in `harvest_onenote()` around `seen_titles` initialization and the `remaining` page budget calculation.

### Verification

Live traces showed Calculus and Stat returning zero newly retained pages while still being enumerated, because their known pages were skipped. This allowed later work to advance into new content on subsequent runs.

---

## BUG-09 — Authentication recovery waited passively and could not restore an expired M365 session

**Layer:** Authentication/recovery  
**Severity:** High when SSO cookies expire  
**Status:** Improved/fixed, with known transient flakes

### What it was

After a browser relaunch, `_wait_for_grid()` could wait for the OneNote grid and click a visible sign-in gate, but it did not always drive the full ClassLink → M365 → credential-form chain. If the M365 cookie was expired, the redirect could remain on a login/picker page indefinitely.

A second contributing issue was that the harvest held `self.lock` for the full walk, preventing the periodic monitor's `auto_reauthenticate()` from acquiring the lock during a long harvest.

### Program impact

- A browser could relaunch successfully but remain unauthenticated.
- The harvest waited hundreds of seconds and then gave up.
- Monitor-driven reauthentication could not run while the harvest held the lock.
- Repeated retries burned time without changing browser state.

### Fix

The recovery path now has a bounded wait budget and invokes the full stored-credential flow when silent SSO is insufficient. `_microsoft_sign_in()` handles the account picker, UPN, ADFS password, iframe-aware form handling, and stay-signed-in step.

The recovery behavior is tri-state: successful recovery continues, a clean non-recoverable state stops retrying, and transient exceptions can trigger relaunch/retry.

### Known residual risk

The M365 flow still has intermittent UI timing failures such as:

```text
Automated M365 sign-in failed: no Sign in button found
```

A retry succeeded on the next attempt. If this becomes frequent, improve the sign-in button wait/locator rather than changing the OneNote page walker.

### Verification

One run failed at the sign-in button, while the immediate retry completed authentication and harvested all three notebooks. This confirms the full flow works but retains a timing-sensitive edge case.

---

## BUG-10 — Harvest service startup raced daemon readiness

**Layer:** systemd/service orchestration  
**Severity:** High for unattended scheduled runs  
**Status:** Fixed in systemd configuration

### What it was

`onenote-harvest.service` had:

```ini
Wants=canvas-browser.service
After=canvas-browser.service
```

For a `Type=simple` daemon, `After=` orders process startup but does not guarantee that the daemon has bound port 8976 or completed initialization. The harvest curl started at the same time as the daemon and got connection refused.

### Observable symptoms

The scheduled service failed with:

```text
onenote-harvest.service: Main process exited, code=exited, status=7/NOTRUNNING
```

Curl exit code 7 means it could not connect to the daemon. No notebook walk occurred.

### Program impact

- An entire scheduled harvest was lost before authentication or page traversal.
- The timer appeared to run, but the cache did not change.
- A daemon restart could incorrectly be interpreted as a successful harvest trigger.

### Fix

A systemd drop-in was added at:

```text
/etc/systemd/system/onenote-harvest.service.d/override.conf
```

It waits up to 120 seconds for the daemon health endpoint:

```ini
[Service]
ExecStartPre=/bin/sh -c 'for i in $(seq 1 60); do curl -sf -m 2 http://127.0.0.1:8976/health >/dev/null 2>&1 && exit 0; sleep 2; done; echo "daemon /health not ready after 120s" >&2; exit 1'
```

The service unit's harvest cap was also changed from `max_pages=100` to `max_pages=300`.

### Verification

After reloading systemd, the health gate passed before the manual harvest started. Future scheduled runs now wait for an HTTP-ready daemon instead of relying on process ordering alone.

---

## BUG-11 — `max_pages=100` could starve later notebooks

**Layer:** Harvest scheduling/performance  
**Severity:** Medium to high depending on page volume  
**Status:** Mitigated

### What it was

The systemd unit requested:

```text
/onenote/harvest?max_pages=100
```

Notebook order is Calculus, Biology, then Stat. A large influx of new Calculus pages could consume all 100 slots before Biology was reached.

### Program impact

- Biology could still be skipped even after its DOM bugs were fixed.
- Stat could receive no new-page budget.
- Results depended on notebook order and teacher activity rather than only on correctness.

### Fix

The service request was raised to:

```text
/onenote/harvest?max_pages=300
```

Cross-run resume remains important because the larger cap is not a substitute for skipping known pages.

### Verification and limitation

The live run that eventually harvested Biology had already started with the previous cap and spent substantial time on new Calculus pages. The 300-page cap applies to subsequent scheduled/manual service requests, not to an already-running request.

If fairness between notebooks becomes important, consider per-notebook budgets or round-robin scheduling instead of only increasing the global cap.

---

## BUG-12 — Per-notebook diagnostics existed only in the HTTP response

**Layer:** Observability/operations  
**Severity:** Medium, but high during incident response  
**Status:** Fixed

### What it was

The harvest accumulated useful trace entries with bare `trace.append(...)`. Those entries were returned only in the HTTP response body. Long curls frequently timed out or were killed when the agent session ended, so the most important diagnostics disappeared with the client.

### Program impact

- Operators could see only “0 pages” or “harvest failed” without knowing which notebook or section caused it.
- A dead client made an otherwise completed server-side harvest look lost.
- Root-cause analysis was repeated unnecessarily.

### Fix

Important per-notebook events are now sent through the logging helper as well as appended to the response trace. Examples include:

```text
expanded 10 section group(s)
sections [...]
0 pages, 0 tasks
```

The systemd harvest service also captures the final JSON response in its journal.

### Verification

The full response from a completed service-owned harvest was recovered with:

```bash
journalctl -u onenote-harvest.service -o cat
```

This exposed the exact Biology trace even though the original client session had ended.

---

## BUG-13 — Orphaned Xvfb display/lock prevented daemon startup

**Layer:** Runtime environment  
**Severity:** Critical operationally  
**Status:** Recovered; prevention still needed

### What it was

Probe scripts created an Xvfb server on display `:99`. When a probe was killed or its parent shell exited, the Xvfb process and/or lock could remain:

```text
/tmp/.X99-lock
/tmp/.X11-unix/X99
```

The daemon then failed when trying to start its own virtual display.

### Observable symptoms

Systemd repeatedly restarted the service, with errors like:

```text
RuntimeError: Could not start the Canvas virtual display.
```

Firefox never reached the authentication phase.

### Program impact

- The browser daemon was unavailable.
- Health checks returned empty or connection failures.
- Harvest requests failed before reaching OneNote.
- A correct application fix could not be tested until the display lock was cleared.

### Recovery

Use a self-match-safe process pattern and clear only the known display lock:

```bash
pkill -9 -f "[X]vfb"
sudo -n rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
sudo -n systemctl restart canvas-browser.service
```

Do not use `pkill -f "Xvfb"` in the same shell command that contains the literal string `Xvfb`; the pattern can match and kill the shell issuing the command.

### Residual risk

Probe scripts should ideally use a unique temporary display or guarantee cleanup in `finally` blocks. The daemon and probes should not share a display/profile without explicit lifecycle management.

---

## BUG-14 — Excess Cline memory usage increased browser instability risk

**Layer:** Host environment  
**Severity:** Medium operational risk  
**Status:** Mitigated

### What it was

A Cline process used approximately 2.5 GiB of RAM and about 2 GiB of swap. This increased memory pressure while Firefox, Xvfb, geckodriver, and the daemon were active.

### Program impact

- Increased swap usage and reduced available memory for Firefox.
- Made browser responsiveness and timing less predictable.
- Increased suspicion that Firefox was being OOM-killed.

### Evidence

The process was killed and swap usage dropped substantially. However, the kernel log check was empty for OOM or Firefox kills:

```bash
dmesg -T | grep -i -E "oom|killed process|firefox"
```

Therefore memory pressure was a contributing environment problem, not the confirmed cause of the OneNote browsing-context failures.

### Recommendation

Keep unnecessary agent daemons stopped during long browser harvests. Monitor memory, swap, Firefox RSS, and geckodriver lifetime separately before attributing a Selenium exception to OOM.

---

## BUG-15 — Merge conflict markers temporarily broke Python imports

**Layer:** Repository/operations  
**Severity:** Critical during deployment/testing  
**Status:** Resolved by the parallel merge workstream

### What it was

During branch reconciliation, several files temporarily contained unresolved Git conflict markers such as:

```text
<<<<<<<
=======
>>>>>>> fix/2026-07-bug-audit
```

Files observed during the investigation included `config.py`, `utils.py`, and several test files.

### Program impact

- Python compilation failed with syntax errors.
- Pytest collection failed before tests could execute.
- Restarting the daemon while an imported runtime module contained markers could have caused a crash loop.
- It was difficult to distinguish application regressions from merge-state corruption.

### Safe detection

```bash
grep -rln '^<<<<<<< \|^>>>>>>> ' --include='*.py' .
git status --short
```

Before restarting the daemon, at minimum compile/import its dependency chain:

```bash
venv/bin/python -m py_compile scripts/canvas_browser_daemon.py
venv/bin/python -c 'import sys; sys.path.insert(0, "scripts"); import canvas_browser_daemon'
```

### Final state

The merge reconciliation later reported zero unresolved `UU`/`AA` files. This issue was repository-state corruption during a concurrent merge, not a defect in OneNote itself.

---

## 4. Diagnoses explicitly ruled out

### Not an OOM-killed Firefox

The kernel reported no OOM or killed-process entries. The relevant `dmesg` filter was empty. Firefox memory pressure existed earlier because of Cline, but it did not explain the discarded browsing context.

### Not a single “killer page”

A standalone probe navigated to `Untitled Page`, the page immediately after `New Seats!` in AP Calculus. The page rendered approximately 266 KB of panel HTML, and the session stayed alive. The probe exited successfully.

The actual iframe and selection failures occurred at variable locations and were reproducible without a particular page.

### Not exclusively an authentication bug

Authentication did fail transiently on some runs, including a missing sign-in-button condition. However, successful retries reached the notebook grid and reproduced the separate Biology DOM failures. Authentication recovery was improved, but it was not the root cause of the zero-page Biology result.

### Not a permanently dead browser tab

When the discarded-context exception occurred, the tab dump showed the ClassLink, OneNote, and SharePoint tabs alive. The stale iframe context was the problem, not necessarily the browser process or tab.

---

## 5. Hard-won OneNote DOM facts

These facts are important before changing selectors or writing another probe.

### Plain notebooks versus Class Notebooks

Plain notebooks such as Calculus and Stat expose sections in a simpler form, commonly matching `.sectionListItem`. Biology is a Class Notebook and uses nested Fabric tree structures.

### Section groups

A section group is a navigation tree node, not a page-bearing section. It may expose:

- `aria-expanded="false"` or `aria-expanded="true"`
- classes containing `sectionGroup` or `groupItemWrap`
- a child group/tree container
- a chevron or expander

Clicking a group should expand it and reveal children. The walker must not wait for page items immediately after selecting a group.

### Leaf sections

Biology leaf entries appeared with classes resembling:

```text
navItem ... navItem__item ... sectionItem
```

They can be nested under one or more section groups. They must be selected using the event pattern proven by the probe.

### Page list

The page list is represented by:

```text
.pageListItem
```

and the surrounding panel includes:

```text
#PageList
.pagesContainer
```

The panel itself can exist while empty. Presence of the panel is not proof that a section was selected.

### Editor iframe

The editor uses `WebApplicationFrame`. OneNote can rebuild it after navigation. Every editor operation must tolerate re-anchoring.

### Timing

Cold SharePoint/OneNote loads can require approximately 60 seconds before the rail exists. Group expansion can require an additional settling period. Page-list waits should be bounded, but a short timeout should be paired with a verified activation strategy rather than treated as proof that a section is empty.

---

## 6. Operational runbook for the next agent

### Check service health

```bash
systemctl is-active canvas-browser.service
curl -s -m 5 http://127.0.0.1:8976/health
systemctl is-active onenote-harvest.service
```

Expected browser health resembles:

```json
{"authenticated": true, "location": "'Canvas LMS' at https://forsyth.instructure.com/"}
```

### Check timer status

```bash
systemctl list-timers onenote-harvest.timer --no-pager
```

The timer runs around 02:00 ET and has a randomized delay. Use full dates with `journalctl` when comparing days.

### Run a harvest safely

Prefer systemd ownership so a terminal/client timeout does not terminate the request:

```bash
sudo -n systemctl start --no-block onenote-harvest.service
systemctl is-active onenote-harvest.service
```

Do not use a bare `systemctl start` for a long `Type=oneshot` service unless you intentionally want the command to block until harvest completion.

### Read the result

```bash
journalctl -u onenote-harvest.service --no-pager -o cat
journalctl -u canvas-browser.service --no-pager --since '2026-09-07 02:00'
```

The curl response JSON is written into the harvest service journal. Look for:

- `status`
- `errors`
- `notebooks`
- `path`
- `expanded ... section group(s)`
- `sections [...]`
- `N pages, M tasks`

### Inspect cache counts

The cache is a dictionary, not a list:

```bash
venv/bin/python - <<'PY'
import collections
import json

cache = json.load(open('cache/onenote_page_extractions.json'))
counts = collections.Counter(key.split('/', 1)[0] for key in cache)
print('total:', len(cache))
for notebook, count in counts.most_common():
    print(count, notebook)
PY
```

### Check for unresolved merge markers

```bash
grep -rln '^<<<<<<< \|^>>>>>>> ' --include='*.py' .
git status --short
```

Do not restart a service or trust pytest while runtime modules contain conflict markers.

---

## 7. Agent-specific debugging pitfalls

1. **Do not trust a successful Selenium click.** Confirm application state, selected item, or page-list population.
2. **Do not use bare time values with `journalctl --since` across midnight.** `--since "21:58"` can mean today’s 21:58, not the previous day. Use an ISO timestamp.
3. **Do not run long harvests through a client that may time out.** Use `systemctl start --no-block` and read the service journal.
4. **Do not infer harvest completion from a dead curl.** A `BrokenPipe` may only mean the client disconnected after the daemon completed its work.
5. **Use self-match-safe process patterns.** Use `[X]vfb` and `[f]irefox` when killing/searching by command line.
6. **Stop the daemon before using a probe that needs its Firefox profile.** Otherwise profile locks can make the probe fail for unrelated reasons.
7. **Keep cold-load waits in probes.** Biology's rail may be empty if inspected immediately after navigation.
8. **Check cache schema before counting entries.** The top-level object is keyed by page path; values are task lists.
9. **Separate notebook failure from whole-harvest failure.** Per-notebook isolation is intentional; one notebook may return an error while others continue.
10. **Avoid reintroducing random event hacks.** The mousedown sequence and keyboard fallback were derived from a controlled probe that measured page-list population.

---

## 8. Verification history

### Initial iframe-resilience verification

- Calculus and Stat completed end-to-end.
- Cache grew from 30 to 72 entries.
- 72 markdown pages were retained.
- 80 real dated tasks were extracted.
- No OOM kill evidence was found.

### Biology group diagnosis

- Biology initially reported no sections.
- Probe found two collapsed top-level groups.
- Expansion exposed nested sections and additional groups.
- Treating every discovered item as a leaf caused approximately ten minutes of empty page-list waits.

### Fabric activation diagnosis

- Native click: 0 page-list items; selection remained `Home`.
- Full mouse dispatch: 73 page-list items.
- Keyboard Enter: 73 page-list items.

### Final successful run

The deployed daemon with iframe re-anchoring, group expansion, leaf filtering, Fabric activation, cache safety, and resume behavior eventually produced:

```text
AP Biology Bleier 26-27: 101 pages, 159 tasks
```

The cache reached:

```text
580 total entries
119 AP Calculus AB 2026-2027
115 AP Biology Bleier 26-27
346 AP Stat 25-26
```

The daemon was later confirmed active and authenticated. The harvest timer was active for the next scheduled run.

---

## 9. Remaining risks and recommended follow-up

1. **Run the full test suite after merge reconciliation.** During the investigation, pytest collection was blocked by unresolved conflict markers. The resilience and alert tests should be run now that the merge is resolved.
2. **Verify the next unattended scheduled harvest.** Confirm that the health gate prevents exit-7 startup races and that Biology still reports nonzero pages.
3. **Consider improving authentication waits.** The stored-credential flow succeeded after retries but had a transient “no Sign in button found” failure.
4. **Make probe display cleanup automatic.** Use `try/finally`, unique displays, and explicit Firefox/Xvfb teardown.
5. **Consider fairer page budgeting.** `max_pages=300` reduces starvation but does not guarantee equal notebook allocation.
6. **Preserve journal evidence.** Keep per-notebook trace logging; it is essential when clients disconnect during multi-hour harvests.
7. **Review system security housekeeping separately.** The environment previously contained a broad NOPASSWD sudo rule and an incorrect `SUDO_PASSWORD` entry in `.env`; these are operational/security concerns, not OneNote traversal bugs.

## 10. Bottom line

The original “Biology returns zero pages” symptom was not one bug. It was a layered failure:

```text
Class Notebook groups collapsed
        + group headers treated as leaves
        + Fabric bare click did not select leaves
        + page-list wait hid the silent selection failure
        + response-only traces hid the evidence
```

The browser resilience and persistence bugs independently made the investigation harder and increased data-loss risk. After fixing the layers and verifying with a systemd-owned run, Biology successfully produced 101 pages and 159 tasks. Future changes should preserve the distinction between group expansion, leaf activation, iframe re-anchoring, and cache persistence; changing only one of those areas can recreate the original symptom in a different form.

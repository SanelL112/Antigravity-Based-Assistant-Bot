# Fix Report: Calendar & Dashboard Data Loss (Canvas Sources)

**Date:** 2026-09-10
**Author:** Buffy (Freebuff coding agent)
**Scope:** Two files changed — `ai_processor.py`, `scrapers/canvas_scraper.py`
**Test status:** Full suite **305 passed** after changes (`venv/bin/python -m pytest tests/ -q`)

---

## 1. Symptom

The user reported: *"the calendar service is missing a lot of stuff from Canvas and is cutting out important information in the dashboard."*

Observed evidence at investigation time:

- `latest_digest.txt` showed only 2 tasks under "Needs attention", an empty `📚 **Canvas**` section, and empty Classroom/Announcements/Gmail/GroupMe sections.
- The assignment calendar store (`assignment-calendar/assignment-calendar.sqlite3`, 335 events) was healthy and syncing — the loss was in the **collection query** and the **dashboard digest pipeline**, not the calendar database itself.
- Every nightly digest returned "✅ Nothing new since the last digest" despite live, uncompleted coursework (e.g. "Enzyme lab final draft (1 per group) — due 2026-09-11").

---

## 2. Root Causes (4 distinct bugs)

### Bug 1 — Canvas API query capped at ~14 days out
**File:** `scrapers/canvas_scraper.py` → `_get_calendar_assignments()`

The collector fetched:

```
/api/v1/courses/{id}/assignments?include[]=submission&order_by=due_at&order=asc&per_page=100
```

sorted ascending by `due_at` with `max_pages=1` and then filtered rows through
`_assignment_is_actionable()` (which keeps rows within a ~7-day overdue grace
window). Net effect: the 100-row page is dominated by the Aug–Jan backlog, the
actionable-window filter rejects nearly all of them, and **every assignment
more than ~2 weeks in the future (CANVAS_DUE_SOON_DAYS window upstream) was
silently invisible** — unit tests, WebAssign deadlines, finals.

### Bug 2 — Digest compaction kept only 3 lines per source
**File:** `ai_processor.py` → `_compact_digest_lines(limit=3)`

Raw scraper output (e.g. `canvas_summary.txt` with Missing/overdue, Due soon,
Completed, Announcements, Pages sections) was squeezed to 3 bullets. The first
lines were decorative headers, so virtually no real content survived. This is
why the `📚 **Canvas**` dashboard section rendered empty.

### Bug 3 — Blanket `"due:"` filter dropped dated coursework
**File:** `ai_processor.py` → `_deterministic_digest()`

```python
if source_key in {"canvas", "classroom"}:
    lines = [line for line in lines if "due:" not in line.lower()]
```

Any Canvas/Classroom line containing "due:" was removed from per-source
sections on the theory that dated work "is already shown in Needs attention."
In practice this hid:

- Missing/overdue items older than the 7-day Needs-attention lookback (e.g. the Aug 14 Academic Integrity items),
- Due-soon items past the 5-item Needs-attention cap,
- Announcements and other dated prose.

### Bug 4 — Seen-bullet dedup suppressed recurring assignments forever
**File:** `ai_processor.py` → `assemble_digest()`

The persistent `cache/seen_bullets.json` set stored every bullet ever shown.
Any bullet seen once was suppressed on every later run — *forget once,
hidden forever*. Live coursework that legitimately re-appears in each digest
until its due date was permanently hidden after first appearance. The live
cache held 571 entries including "Enzyme lab final draft", "1SP - Replace
Random", etc. A secondary effect: when *all* bullets were suppressed, the
digest was replaced entirely with "✅ Nothing new since the last digest."

---

## 3. Fixes Applied

### Fix 1 — Window-anchored Canvas query with fallback
**File:** `scrapers/canvas_scraper.py`, `_get_calendar_assignments()` (~line 1196)

The query now anchors the due-date range so Canvas returns the *entire relevant
schedule* rather than the first page of a backlog-sorted list:

```
&due_at[{window_start}..{window_end}]
```

- `window_start` = `now - CANVAS_ASSIGNMENT_OVERDUE_GRACE_DAYS` (default 7)
- `window_end` = `now + CANVAS_CALENDAR_WINDOW_DAYS` (new setting, default 180)
- The per-assignment `_assignment_is_actionable()` check still runs, so
  prior-year/stale rows stay filtered.
- **Defensive fallback:** if the windowed query returns empty (e.g. an
  deployment whose Canvas ignores the range filter), the code retries once
  without the range so the feed can never go fully blank due to the new param.
- `overdue_grace` is read once at the top of the function (~line 1171).

### Fix 2 — Compaction keeps real content, drops only pure headers
**File:** `ai_processor.py`, `_compact_digest_lines()` (line 573)

- Default limit raised 3 → **8** lines per source section.
- New module-level `_HEADER_LINE_RE` (line 564) matches decorative sub-headers
  (`🎯 Canvas: What to do next`, `🚨 Missing / overdue`, `📅 Due soon`,
  `✅ Recently completed`, `📢 Canvas announcements`, etc.) **anchored to the
  whole line** so only pure header lines are dropped — content lines that
  merely contain those words survive.
- Empty-source markers and repeated source headings are still filtered as before.

### Fix 3 — Duplicate suppression only for exact (title, date) pairs
**File:** `ai_processor.py`, `_deterministic_digest()` (lines 665–675)

Replaced the blanket `"due:"` substring filter with a precise rule: a line is
suppressed only when its own `(title, due_date)` pair is among the exact
`(title, due_date)` pairs already shown in the Needs-attention highlight
(`tasks[:5]`):

```python
dated_pair_re = re.compile(
    r"^(?:\[[^\]]*\]\s*)?(.*?)\s*[—–-]\s*Due:\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
highlighted = {(t["title"].strip().lower(), t["due_date"]) for t in tasks[:5]}
```

Dated-but-not-highlighted items (overdue work, due-soon beyond cap) now render
in the Canvas section again.

### Fix 4 — Refresh-based deduplication with timestamps
**File:** `ai_processor.py`, `assemble_digest()` (dedup block, lines 752–815)

`seen_bullets.json` semantics changed from *forget-once-forever set* to
*refresh-based timestamped map*:

- Format: `{ "normalized bullet": last_seen_unix_ts, ... }`.
- A bullet that reappears in the freshly assembled digest is **shown again**
  and its timestamp renewed — recurrence in the live digest proves the item is
  still current. Only *new* bullets increment the "new this run" log counter.
- Entries older than `DIGEST_BULLET_STALE_DAYS` (env var, default **7**) are
  pruned at load time.
- Legacy list-format files (string array) are migrated on load: every existing
  entry is treated as fresh (`now` timestamp), then persisted in dict form.
- Persistence caps at 5000 entries as before (evicting oldest by timestamp).
- The "✅ Nothing new" wholesale replacement of the digest was removed; the
  deduped digest is always written through. ("From your notebooks" append
  behavior and `latest_digest.txt` write are unchanged.)

Note: normalization is unchanged (`[^\\w\\s]` stripped, lowercased), so the
same-bullet match behavior is identical to before — only *suppression
duration* changed.

---

## 4. Verification Performed

1. **Full test suite:** `venv/bin/python -m pytest tests/ -q` → **305 passed**, 0 failures (includes `test_task_hub.py`, `test_digest_task_extraction.py`, `test_assignment_calendar.py`, `test_canvas_features.py`).
2. **Replay with live data:** loaded the real `cache/canvas_summary.txt`, `classroom_summary.txt`, `groupme_summary.txt`, etc. and ran `_deterministic_digest()`. Result: Needs attention shows the 5 current tasks; `📚 **Canvas**` now shows the 8 missing/overdue Academic Integrity rows; Announcements/GroupMe/Notion sections all render content.
3. **Legacy migration test:** copied the real 571-entry list-format `seen_bullets.json` into a sandbox and exercised the new load/migrate/renew/persist logic. Confirmed: recurring bullets remain visible, new bullet detection still works, persisted file converts to timestamped dict.

---

## 5. Config / Env

| Setting | Default | Purpose |
|---|---|---|
| `CANVAS_CALENDAR_WINDOW_DAYS` | `180` | How far ahead the calendar collector queries Canvas assignments (new). |
| `DIGEST_BULLET_STALE_DAYS` | `7` | How long a suppressed digest bullet ages before re-notification is possible (new). |
| `CANVAS_ASSIGNMENT_OVERDUE_GRACE_DAYS` | `7` (existing) | Overdue lookback; also now anchors the Canvas query window start. |

Both new knobs are read via `get_setting` / `os.getenv` at call time, so they can be tuned without code changes.

---

## 6. Known Remaining Issues

1. ~~**Junk-titled calendar events from syllabus prose.**~~ **RESOLVED
   2026-09-10 (same day).** `_JUNK_TITLE_RE` was tightened in both
   `scrapers/assignment_calendar.py` and `scrapers/canvas_page_extractor.py`
   and both modules gained a shared-by-mirror `_prose_title_reject()` layer:
   percent/equation rows, question-opener note fragments, third-person
   outcome statements, topic lists, and lesson-text sentences are now
   rejected, with a task-keyword exemption (`quiz/test/homework/reading/
   essay/project/lab/report`) guarding real titles. Verified against the
   live store: 95/335 rows would now be rejected, 0 false positives across
   a 32-title real-task keep list. Regression tests:
   `tests/test_junk_title_filter.py` (161 cases, including a gate/extractor
   parity tripwire). The ~95 existing junk rows in
   `assignment-calendar.sqlite3` (and their CalDAV/Google mirrors) are
   cleaned by the next `prune_duplicates_and_junk()` run — triggered
   automatically by every `sync_all()`.
2. **Notion tasks in the digest lag** (e.g. "Due: 2026-09-04" items still
   listed on 2026-09-10) — appears to be Notion-side status sync, separate from
   the Canvas pipeline.
3. **`canvas_page_extractions.json` has 259 hash-keyed vs 42 section-keyed
   entries** with a 300-entry global cap — old section keys can be evicted;
   worth reviewing the cache-eviction ordering if extraction recall ever
   drops again.

### 6a. Junk-filter maintenance notes

- The prose filter exists as hand-mirrored copies in two modules (a back-
  import would be circular: `assignment_calendar` already imports the
  extractor lazily). `test_gate_and_extractor_stay_in_sync` fails on drift.
- The extractor runs prose rejection on the FULL row BEFORE length
  truncation; truncation can otherwise cut away the very phrase that marks a
  row as prose. The gate never truncates, so this ordering is required for
  parity.
- `_SENTENCE_OPENER_RE` entries must stay qualified (e.g. `students?\s+
  (?:will|...)` — never bare `students?\b`): bare forms reject real titles
  like "Student Council Application". The task-keyword exemption only
  applies inside `_prose_title_reject`, not to direct opener matches.

---

## 7. Rollback

The change set is small and self-contained (`ai_processor.py`,
`scrapers/canvas_scraper.py`). Reverting those two files restores prior
behavior.

`cache/seen_bullets.json` is forward/backward compatible across the format
change: the old code reads it with `set(json.loads(...))`, and `set()` over a
dict yields its keys, so a post-fix (dict-format) cache file still loads
correctly under the pre-fix code (losing only the timestamps). No manual cache
surgery is required in either direction.

---

## 8. Data Files Touched at Runtime (not in git)

- `cache/seen_bullets.json` — auto-migrates list → dict on first post-fix digest.
- `assignment-calendar/assignment-calendar.sqlite3` — untouched by these fixes.

**Update (2026-09-10, later):** the junk-filter follow-up (§9) did touch the
calendar database: 95 junk events were pruned (335 → 240). §6 issue #1 is
resolved; see §9 for details.

---

## 9. Junk-Filter Tightening — Follow-Up (2026-09-10, later the same day)

Issue #1 above was executed on immediately after this report was written.

**Files changed:** `scrapers/assignment_calendar.py`,
`scrapers/canvas_page_extractor.py` (mirrored changes), plus new test file
`tests/test_junk_title_filter.py`. Full suite after: **473 passed, 0
failures** (was 305 before the follow-up; the new filter test file
contributes 161 cases).

### What changed

Both modules received the same three-part change (the copies are hand-
mirrored; `test_gate_and_extractor_stay_in_sync` fails on drift):

1. **`_JUNK_TITLE_RE` extended** with `important topics`, `main ideas`,
   `guiding questions`, `college readiness`, `final exam exemptions`.
2. **New `_prose_title_reject()` layer** catching what anchored regexes
   cannot: any title containing `%`; any `=` that is not a math-work title
   (`_MATHY_TASK_RE` exempts homework/worksheet/practice/problems/equations);
   question openers ("Which type of bond creates..."); third-person outcome
   statements ("Completes BioBuilder project..."); comma-separated topic
   lists (3+ commas, no digits, no task keyword); numbered-list fragments
   ("4. pH 9 is..."); mangled double-agenda rows ("1) X ... 2) Y"); long
   lowercase sentences — with an action-verb carve-out so "Read pages 41-45
   of unit packet" survives; short "The X" headings ("The Nucleus") with the
   same task-keyword exemption.
3. **Task-keyword exemption** (`_PROSE_OPENER_EXEMPT_RE`):
   quiz/quizzes/test(s)/homework/hw/due/reading/essay/project/lab/report
   keeps real titles alive wherever an opener or short-heading rule matches
   ("Chapter 4 Reading Quiz").
4. **Extractor ordering fix:** prose rejection now runs on the FULL row
   BEFORE length truncation. Truncation can cut away the very phrase that
   marks a row as prose (", so describe ..."), which previously caused
   gate/extractor disagreement.

### Verification against live data

- **95 of 335** live store rows matched the tightened filter; **0 false
  positives** across a 32-title keep-list drawn from real events
  ("Review for AP Exam", "Infinite Limits and Limits at Infinity Homework",
  "1.2 Homework", "WA2a", ...).
- `tests/test_junk_title_filter.py`: 161 tests — parametrized reject/keep
  lists for both modules + the parity tripwire.

### Prune executed the same day

With the filter verified, the existing junk events were purged from the live
calendar:

1. **Status check:** sync enabled, CalDAV (canonical) configured, Google
   mirror off — writes were local-only.
2. **Backup:** `assignment-calendar.sqlite3.bak-20260910-191111` snapshot
   taken before any write.
3. **Dry run** (read-only replication of the prune logic): exactly 95
   removals, 100% junk — 0 stale deadlines (>21d past), 0 residual
   duplicates, 0 task-like prefixes in the removal set.
4. **Ran `prune_duplicates_and_junk()` for real:** deleted the 95 events
   from the SQLite store AND their matching CalDAV events from the Radicale
   calendar.
5. **Verified:** `335 → 240` events, 0 junk titles remaining in the store.
   The upcoming view was then real work only (Enzyme lab final draft 9/11,
   nine 1SP Canvas practice sets 9/14, AP Bio midpoint quizzes 9/15, TSA
   week, Unit 2 summative 9/25, WA2a 10/8, robotics qualifiers, May AP exam).
6. **Backup deleted** after verification, per user request. The directory
   again contains only the live database.

### Residual junk still in the store (accepted)

A handful of 9/11 syllabus-policy fragments survived the filter — e.g.
"Summative assessments identify standards where", "FCS Code of Conduct
States: Academic dishonesty", "QUARTERLY MISSING ASSIGNMENT DUE DATE". They
come from a broken extraction of the AP Lang syllabus page and will age out
via the 21-day past-due prune; extend `_prose_title_reject` only if future
syllabus crawls produce fresh ones.

### Maintenance cautions

- Never add *bare* word openers to `_SENTENCE_OPENER_RE` (e.g.
  `students?\b`): bare forms reject real titles like "Student Council
  Application". The task-keyword exemption only applies inside
  `_prose_title_reject`, not to direct opener matches. Use qualified forms
  like `students?\s+(?:will|should|can|are|must|may|who|missing)\b`.
- The `_prose_title_reject` copies in the two modules are the sync point;
  the parity test is the tripwire. Update both or neither.

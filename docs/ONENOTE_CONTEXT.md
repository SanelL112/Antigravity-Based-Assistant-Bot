# OneNote + Study-Digest Engineering Context

**For AI agents:** This file captures the state, architecture, and roadmap for the
OneNote pipeline and the study-topic discovery system in
`/home/sanel/personal-assistant-bot`. Read this before editing either system.

---

## 1. What just got fixed (most-recent → ~1h ago)

| Commit | File | Problem | Fix |
|---|---|---|---|
| `97f3bdf` (top of `fix/2026-07-bug-audit`) | `scrapers/topic_discovery.py` | Dated tasks buried under undated page titles; future pure-date titles ("2026-09-10") passing through | Dated topics rank **above** undated; `_is_date_only_title` drops date-only titles in **both** directions |
| `433ea41` | idem | "Aug 24" calendar pages appearing as study topics | `_is_past_date_title`→`_is_date_only_title`: strict dateutil parse drops pure-date titles, keeps "Unit 1 Week 4 Aug 24-28" |
| `38fcd0e` | `scrapers/onenote_surface.py` | Daemon dies silently when Firefox/Surface crashes | Self-healing: relaunches browser; page-title dedupe across sections |
| `4b899c0` | daemon + lfm | Surface hangs on blank/ink PDF pages; index rebuild stalls | Surface timeout honors config (45s→300s for ink) |
| `3bfdac6` | `scrapers/onenote_harvest.py` | Ink pages harvested as empty text | Route to vision when text empty |
| `33cdae3` | `scrapers/onenote_surface.py` | Vision timeout too low for handwriting | 45s→300s |
| `a537060`, `1098d26` | `scrapers/onenote_harvest.py` | Tasks on the page's creation-header date mis-dated | Drop tasks whose due_date == page's own date header |
| `621bbb8` | Surface | Surface stalls the build at 12KB payloads | 12KB chunk + 200ms duty-cycle pauses |
| `1766282` | `lfm.py` (indexer) | Index rebuild stalls on large payloads | Threads=4 (persistent), respects payload budget |
| `3f020d9` | RPC Surface | Logs a URL instead of "(loading)" | Surface logs real URL when ready |

**Live verified (no-online mode): 12 real study topics** — "U1 Test",
"Unit 1 Quiz 1", "Review enzyme lab quiz",
"Complete pgs 3-4 in unit study guide", etc. No "Aug 24" noise.

---

## 2. Three-repo topology

```
/home/sanel
├── personal-assistant-bot/   ← THE daemon (bot.service), Python 3 venv
│   ├── main.py               ← python-telegram-bot entry, schedules digests
│   ├── scrapers/             ← all ingestion: canvas, drive, onenote_*, nightly, mega_study_builder
│   ├── study_features/       ← standalone study-feature scripts (see §4)
│   ├── docs/ONENOTE_CONTEXT.md  ← this file
│   └── docs/archive/AI_CONTEXT.md  ← legacy high-level context
├── pab-ops-staging/          ← systemd unit + infra config (bot.service, syncthing)
├── pab-study-content-staging/← generated study-guides + embeddings (Syncthing → Obsidian)
└── pab-dev/                  ← model weights / lfm checkpoints
```

**Daemon:** `bot.service` (systemd), run via `systemctl restart bot.service`.
Venv at `personal-assistant-bot/venv/`. Python deps in `requirements.txt`.
**Do not run `npm install`.**

---

## 3. OneNote pipeline (as-built)

> ⚠️ **File-name drift vs. docs:** there is no `onenote_harvest.py` or
> `collect_assignments.py` in the current tree.  The harvest lives in
> `scripts/canvas_browser_daemon.py` (`BrowserDaemon.harvest_onenote` +
> `/onenote/harvest` HTTP route); downstream consumers read the JSON it
> writes at `cache/onenote_page_extractions.json`.

### Purpose today (3 live uses)
1. **Calendar source** — `scrapers/assignment_calendar.py` loads the harvest
   cache (`_load_cached_onenote_extractions`) and turns tasks into calendar
   events.
2. **Topic source** — `scrapers/topic_discovery.py` reads OneNote *task* items
   as study-topic candidates (ranked, recent-first).
3. **Dashboard content** — `main.py` study digest + the 12-topic keyboard
   from `discover_topics_per_class`.

### Phase 1 shipped (this branch, uncommitted)
- **RAG retention** — the daemon writes each harvested page's reading-order
  text to `source_cache/onenote_pages/<notebook>/<section>/<page>.md`
  (frontmatter: source, notebook, section, title, date) via
  `scrapers/onenote_web_scraper.save_harvested_page`.  The embedding indexer
  (`scrapers/embedding_indexer.collect_sources`) globs that dir recursively,
  so notebook pages are now searchable memory.
- **New-task Telegram alerts** — `scrapers/onenote_alerts.check_new_onenote_alerts`
  diffs the harvest cache against `cache/onenote_seen_tasks.json` (once-per-
  task dedupe) and `main.py._check_updates_impl` pushes new upcoming items
  through the existing Telegram send path.
- **"From your notebooks" digest section** — `scrapers/onenote_alerts.notebooks_section`
  renders new-pages-this-week (first-seen tracked in
  `cache/onenote_pages_first_seen.json`) + upcoming OneNote items; appended by
  `ai_processor.assemble_digest` after bullet dedup.

### Not yet wired (defenses exist, integration does not)
- Study-guide generator reads only `combined_summaries.txt` +
  `pdf_exports.txt`, **not** OneNote notes.
- Telegram alerts now cover OneNote (+Canvas/Drive); Notion/watcher alerts
  unchanged.

### Harvest flow (as-built)
```
scripts/canvas_browser_daemon.py   (persistent Firefox/ClassLink session, :8976)
   │  /onenote/harvest → crawl_onenote_web → notebooks → sections → pages
   │  per page: #WACViewPanel outerHTML → extract_tasks_from_page
   │        text route (local LLM + heuristic) | ink route (LFM2-VL snapshot)
   │  reading-order text → save_harvested_page → source_cache/onenote_pages/**
   └─ writes  cache/onenote_page_extractions.json  {notebook/section/page: [tasks]}
                tasks dated == page's own date header are dropped  (defect fix a537060)
```

---

## 4. Study-feature sources & storage (current state)

Standalone study features **exist** but are **not yet fed by OneNote**:

- `scrapers/nightly_processor.py` — nightly guide build; input =
  `combined_summaries.txt` + `pdf_exports.txt` (Drive/YouTube). No OneNote.
- `scrapers/mega_study_builder.py` — 50-page textbook generator; source =
  YouTube + web + Drive PDFs. No OneNote.
- `study_features/practice_grader.py` — drill mode; uses generic prompts. No OneNote.
- Embedding/RAG indexer watches `source_cache/` markdown. OneNote markdown is
  not yet written into `source_cache/`.

**Memory model:** append-only markdown only (`mega_index.md`,
`curated_brain.md`) + JSON. No SQL. Indexer is incremental by MD5; full
rebuild ≈ 35 min on the i5.

---

## 5. Defensive filters already in place

| Filter | File | Rule |
|---|---|---|
| `max_total_topics=12` cap | `topic_discovery.py` | Combined topic list ≤ 12 (Telegram limit) |
| Window: today → +60d | idem | A class qualifies only if it has work in the next 60 days |
| Dated-above-undated ranking | `_deterministic_topics` | Dated topics come first, sooner-before-later; undated pages demoted |
| Date-only titles dropped | `_is_date_only_title` | Pure-date titles ("Aug 24", "2026-09-10") dropped; "Unit 1 Week 4 Aug 24-28" kept |
| Junk keyword filter | `_deterministic_topics` | titles matching advisement/syllabus/handbook/observe/signature skipped |
| Hash-key skip | idem | 16-hex SHA page-id titles skipped |
| Page-header-date dedupe | `onenote_harvest.py` | Tasks dated == a page's own date header are dropped |

---

## 6. Feature roadmap (recommended build order)

### Phase 1 — small diffs, immediate value ✅ shipped (uncommitted)
1. **Note retention → searchable memory (RAG).** ✅
   `save_harvested_page` (daemon) → `source_cache/onenote_pages/` →
   `embedding_indexer.collect_sources` recursive glob.
2. **Telegram alerts for new OneNote tasks.** ✅
   `onenote_alerts.check_new_onenote_alerts` + `main.py._check_updates_impl`;
   seen-id dedupe in `cache/onenote_seen_tasks.json`.
3. **"From your notebooks" digest section.** ✅
   `onenote_alerts.notebooks_section` appended in `assemble_digest`
   (new pages this week + upcoming items).

### Phase 2 — medium effort (needs Phase 1)
4. **OneNote as a study-guide source.** Feed `internal_notes` from OneNote into
   `mega_study_builder.py` (currently only reads combined_summaries.txt +
   pdf_exports.txt).
5. **Notes-grounded drill mode.** `practice_grader.py` generates questions from
   *this week's actual notes* instead of generic prompts.

### Phase 3 — expensive, compounds over time
6. **Ink transcription pipeline.** LFM2VL reads handwriting; a transcription
   prompt ("convert handwritten note to clean markdown") cleans notes.
   Runs nightly, ~2 min/page on the Surface.

### Phase 4 — once 1–3 prove out
7. Cross-source correlation (OneNote pages ↔ Canvas assignments).
8. Missing-work radar: OneNote-mentioned deadlines vs Canvas submissions.
9. Auto-generated flashcards (AnkiConnect or JSON export).

---

## 7. Hard environment facts

- **Host:** Debian; Python 3 venv at `personal-assistant-bot/venv/`.
- **Daemon:** `bot.service` (systemd); restart via `systemctl restart bot.service`.
- **API keys:** `OPENROUTER_API_KEY` for online topic *naming* only. If absent,
  `topic_discovery.py` returns deterministic candidates (never empty).
- **Model chain:** OpenRouter nvidia/nemotron-ultra (primary), fallback nano,
  local flash/pro for heavy reasoning/study-guide generation.
- **Surface:** handwriting scan source for ink pages; 4 threads, 12KB payload
  chunks, 200ms duty-cycle pauses. Vision timeout configurable (300s for ink).
- **Power:** i5-class CPU; embedding rebuild budgeted 1AM nightly (~35 min).
- **Telegram limit:** 4096 chars; digest capped at 12 topics.
- **Syncthing:** maps strictly to `study_guides/` → Obsidian. Never write temp
  files there; use `source_cache/`.

## 8. Test hygiene

- `tests/test_topic_discovery.py` = source of truth for ranking/date filters.
- `tests/test_onenote_alerts.py` = source of truth for alert/section/retention
  rules (window math, once-per-task dedupe, first-seen tracks, junk filters).
- Add a test for any new ranking or filter rule before merging.
- After edits: `venv/bin/python -m pytest tests/test_topic_discovery.py -q`
  must be green; full suite `venv/bin/python -m pytest tests/ -q`.
- Current full-suite count: 261 passing (was 247).
# Branch Merge & Reconciliation Handoff Guide

**Date:** 2026-09-05  
**Repository:** `personal-assistant-bot` (`SanelL112/pab-core`)  
**Target Branch:** `main` (`origin/main`)  
**Source Branch:** `fix/2026-07-bug-audit` (`origin/fix/2026-07-bug-audit`)  
**Audience:** Future AI coding assistant tasked with merging and reconciling both branches.

---

## 1. Executive Summary & Objective

The codebase currently has two divergent, highly developed branches:

1. **`main` (`origin/main` @ `a917c00`)**:
   Contains security hardening, dependency remediations (Pillow 12.3.0, pypdf 6.15.0), watchdog attachment initialization, isolated runtime deployments, fail-closed private cloud routing, and privacy/audit test suites.
2. **`fix/2026-07-bug-audit` (`origin/fix/2026-07-bug-audit` @ `af1aa05`)**:
   Contains 70+ commits building the persistent browser daemon (`scripts/canvas_browser_daemon.py`), OneNote ClassLink SSO & SharePoint frame recovery, Class Notebook nested section group crawling (`role="treeitem"` with child containers), reading-order RAG retention in `source_cache/onenote_pages`, Telegram alert integration, and study digest generation.

**Goal:** Merge `fix/2026-07-bug-audit` into `main` without regressing either branch's capabilities, keeping all security enhancements, scraper architectures, daemon features, and test coverage intact.

---

## 2. Common Ancestor & Divergence Stats

- **Merge Base:** `a8f94ac40336fce5960e0f0c0eb7723414b17407`
- **Commits on `main` ahead of base:** 16 commits (security hardening, pypdf/pillow bumps, watchdog, privacy).
- **Commits on `fix/2026-07-bug-audit` ahead of base:** 70+ commits (daemon lifecycle, OneNote pipeline, study creator).
- **In-Memory Conflict Check (`git merge-tree`):** Conflicts across ~30 files spanning bot runtime, configuration, test suites, and scrapers.

---

## 3. Critical Reconciliation Rules by Subsystem

When resolving merge conflicts, follow these authoritative rules:

### A. Core Entry & Orchestration (`main.py`)
- **From `main`:** Keep the watchdog integration (`run_watchdog.py`), isolated deployment hooks, and graceful exception wrapping.
- **From `fix/2026-07-bug-audit`:** Keep OneNote periodic task alerts (`scrapers.onenote_alerts.check_new_onenote_alerts`), correlation tracking, and browser daemon health checks.
- **Rule:** Both pipelines must execute in the background loop without blocking each other.

### B. AI & Digest Processing (`ai_processor.py`)
- **From `main`:** Retain privacy scrubbing (PII redaction) and fail-closed cloud routing.
- **From `fix/2026-07-bug-audit`:** Retain the deterministic `"From your notebooks"` digest section (`scrapers.onenote_alerts.notebooks_section`), study topic buttons, and Surface RPC rate pacing.
- **Rule:** The notebook digest section must be appended after dedup so notebook material is never omitted when available.

### C. Configuration & Settings (`config.py` & `.env.example`)
- **From `main`:** Keep `ISOLATED_DEPLOYMENT`, `PII_MASKING_ENABLED`, and cloud routing fallback parameters.
- **From `fix/2026-07-bug-audit`:** Keep `CANVAS_VIRTUAL_DISPLAY`, `CANVAS_REAUTH_COOLDOWN_SECONDS`, RPC timeout tunables (`RPC_SURFACE_TIMEOUT`), and OneNote cache paths.
- **Rule:** Unify settings into `config.py` with safe defaults; never drop environment variable lookups needed by either side.

### D. Scrapers & Harvesters (`scrapers/`)
- **`scrapers/canvas_scraper.py`:**
  - Keep low-memory tab unloading prevention (`browser.tabs.unloadOnLowMemory = False` and `browser.tabs.min_inactive_duration_before_unload = 1800000`) from `fix/2026-07-bug-audit`.
  - Keep Canvas course discovery and slide text parsing.
- **`scrapers/onenote_web_scraper.py` & `scrapers/onenote_alerts.py`:**
  - Keep all OneNote reading-order extraction and `save_harvested_page` functions writing to `source_cache/onenote_pages/`.
- **`scrapers/embedding_indexer.py`:**
  - Keep recursive scanning of `source_cache/onenote_pages` alongside the standard `academic_notes/` directory.
- **`scrapers/offline_indexer.py` & `scrapers/web_precacher.py`:**
  - Retain the privacy and offline guards added in `main`.

### E. Daemon & Probes (`scripts/`)
- **`scripts/canvas_browser_daemon.py`:**
  - Preserved in full from `fix/2026-07-bug-audit`.
  - Must include:
    1. Automatic stale `/tmp/.X{N}-lock` resolution in `VirtualDisplay.start()`.
    2. `_editor_js()` retry loop with `#WebApplicationFrame` re-anchoring.
    3. Section group classification (`role="treeitem"`, `aria-expanded`, child containers).
    4. Group expansion recursion without querying `.pageListItem` on headers.
    5. 10s maximum timeout on page list queries.
    6. Cross-run title resume and cache merging (`onenote_page_extractions.json`).
- **OneNote Probes (`scripts/probe_biology_*.py`, `scripts/isolate_killer_page.py`):**
  - Keep these scripts intact in `scripts/` as operational diagnostic tools.

### F. Dependencies (`requirements.txt`)
- Accept the newer, patched versions from `main`:
  - `pypdf>=6.15.0` (replaces EOL `PyPDF2`)
  - `Pillow>=12.3.0`
- Keep any daemon/selenium/async requirements from `fix/2026-07-bug-audit`.

### G. Test Suite (`tests/`)
- Both test suites MUST be retained and unified:
  - From `fix/2026-07-bug-audit`: `tests/test_harvest_resilience.py`, `tests/test_onenote_alerts.py`.
  - From `main`: `tests/test_p0_security.py`, `tests/test_routing_privacy.py`, `tests/test_reliability.py`, `tests/test_main_fixes.py`, `tests/test_dep01.py`.
- **`pytest.ini`:** Include `pythonpath = .` so all tests resolve imports cleanly.

### H. Deleted/Legacy Files (Modify/Delete Conflicts)
- The audit branch deleted obsolete one-off scripts:
  `audit_script.py`, `clean_emojis.py`, `comprehensive_test.py`, `fix_bot_commands.py`, `fix_utils_pii.py`.
- **Resolution:** Confirm they are truly unused by the current daemon/bot entry points, and accept their deletion in the final tree.

---

## 4. Step-by-Step Reconciliation Protocol

Execute this procedure in a dedicated session:

### Step 1: Prepare Clean Workspace
```bash
# Verify daemon service status
systemctl status canvas-browser.service --no-pager

# Ensure git status on fix/2026-07-bug-audit is completely clean
git status
```

### Step 2: Create a Merge Reconciliation Branch
Do NOT merge directly on `main`. Create an integration branch:
```bash
git checkout -b reconcile/merge-bug-audit-into-main origin/main
git merge --no-commit fix/2026-07-bug-audit
```

### Step 3: Resolve File Conflicts Systematically
Go through conflicted files using the rules in Section 3:
1. **Config & Environment:** `.gitignore`, `requirements.txt`, `config.py`, `.env.example`.
2. **Bot & AI:** `main.py`, `ai_processor.py`, `llm_router.py`, `bot/`.
3. **Scrapers & Tools:** `scrapers/*`, `scripts/*`, `utils.py`, `telegram_logger.py`.
4. **Tests:** `tests/conftest.py`, `pytest.ini`, keep all test files from both sides.
5. **Deleted Scripts:** `git rm` obsolete one-off scripts (`audit_script.py`, etc.).

### Step 4: Verification Suite
Once all conflicts are marked resolved:
```bash
# 1. Syntax check all modified Python files
python3 -m py_compile scripts/canvas_browser_daemon.py main.py ai_processor.py config.py

# 2. Run targeted test suites
venv/bin/pytest tests/test_harvest_resilience.py tests/test_onenote_alerts.py -v
venv/bin/pytest tests/test_p0_security.py tests/test_routing_privacy.py -v

# 3. Run full test suite
venv/bin/pytest tests/ -v
```

### Step 5: Service Sanity Check
```bash
# Verify canvas-browser.service runs with the reconciled code
sudo systemctl restart canvas-browser.service
sleep 3
curl -s http://127.0.0.1:8976/health
```

### Step 6: Commit and Push to Main
```bash
git commit -m "chore(merge): reconcile fix/2026-07-bug-audit into main"
git checkout main
git merge reconcile/merge-bug-audit-into-main --ff-only
git push origin main
```

---

## 5. Known Pitfalls & Do-Not-Dos

1. **Do not run blind `git merge -X ours` or `-X theirs`**: Both sides contain vital code (daemon functionality on one side, security/dependency fixes on the other).
2. **Do not stage dirty `academic_notes/` files indiscriminately**: Those files are continually refreshed by background scraping; only stage files intentionally touched.
3. **Do not remove `VirtualDisplay` stale lock cleanup**: Without `/tmp/.X99-lock` unlinking, a system crash or ungraceful shutdown causes an infinite systemd restart loop.
4. **Do not lower the 10s page list timeout**: Biology leaf sections mount quickly (<3s), while group headers never mount `.pageListItem`. A 10s ceiling prevents hung crawler subshells.

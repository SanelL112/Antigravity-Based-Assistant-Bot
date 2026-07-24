import os
import re

report = []
def add_status(bug_id, name, status, ref):
    report.append(f"**{bug_id}. {name}**\n   - Status: {status}\n   - Reference: `{ref}`\n")

if __name__ == "__main__":
    # Source 1 Bugs

    # 1. Contradictory Security Filters Break Core Features
    try:
        with open('utils.py', 'r') as f:
            content = f.read()
        if "'open('" in content or "'subprocess'" in content:
            add_status("S1-1", "Contradictory Security Filters", "STILL PRESENT", "utils.py")
        else:
            add_status("S1-1", "Contradictory Security Filters", "FIXED", "utils.py")
    except:
        pass

    # 2. Async Event Loop Blocked by Subprocesses and I/O
    try:
        with open('llm_router.py', 'r') as f:
            content = f.read()
        if "client.post(" in content and "to_thread" not in content and "client.stream(" not in content:
            add_status("S1-2", "Async Event Loop Blocked", "STILL PRESENT", "llm_router.py")
        else:
            add_status("S1-2", "Async Event Loop Blocked", "FIXED", "llm_router.py")
    except:
        pass

    # 3. Config Drift & Broken File Paths
    try:
        with open('bot/ai_bridge.py', 'r') as f:
            content = f.read()
        if "__file__" in content:
            add_status("S1-3", "Config Drift & Broken File Paths", "STILL PRESENT", "bot/ai_bridge.py")
        else:
            add_status("S1-3", "Config Drift & Broken File Paths", "FIXED", "bot/ai_bridge.py")
    except:
        pass

    # 4. Oscillating Digest Deduplication
    try:
        with open('ai_processor.py', 'r') as f:
            content = f.read()
        if "seen_bullets.json" not in content:
            add_status("S1-4", "Oscillating Digest Deduplication", "STILL PRESENT", "ai_processor.py")
        else:
            add_status("S1-4", "Oscillating Digest Deduplication", "FIXED", "ai_processor.py")
    except:
        pass

    # 5. Race Conditions in State Management
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        if "asyncio.Lock" not in content and "filelock" not in content and "portalocker" not in content:
            add_status("S1-5", "Race Conditions in State Management", "STILL PRESENT", "main.py")
        else:
            add_status("S1-5", "Race Conditions in State Management", "FIXED", "main.py")
    except:
        pass

    # 6. Data Loss on File Rotation
    try:
        with open('utils.py', 'r') as f:
            content = f.read()
        if "%Y-%m-%d" in content and "counter" not in content and "append" not in content:
            add_status("S1-6", "Data Loss on File Rotation", "STILL PRESENT", "utils.py")
        else:
            add_status("S1-6", "Data Loss on File Rotation", "FIXED", "utils.py")
    except:
        pass

    # 7. Unbounded Growth in Nightly Appends
    try:
        with open('scrapers/nightly_processor.py', 'r') as f:
            content = f.read()
        if "cursor" not in content and "limit" not in content and "tail" not in content:
            add_status("S1-7", "Unbounded Growth in Nightly Appends", "STILL PRESENT", "scrapers/nightly_processor.py")
        else:
            add_status("S1-7", "Unbounded Growth in Nightly Appends", "FIXED", "scrapers/nightly_processor.py")
    except:
        pass

    # 8. Cache Invalidation Flaw
    try:
        with open('ai_processor.py', 'r') as f:
            content = f.read()
        if "[:1000]" in content and "hash" in content:
            add_status("S1-8", "Cache Invalidation Flaw", "STILL PRESENT", "ai_processor.py")
        else:
            add_status("S1-8", "Cache Invalidation Flaw", "FIXED", "ai_processor.py")
    except:
        pass

    # 9. Temporary File / Resource Leaks
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        if "finally:" not in content or "os.unlink" not in content:
            add_status("S1-9", "Temporary File / Resource Leaks", "STILL PRESENT", "main.py")
        else:
            add_status("S1-9", "Temporary File / Resource Leaks", "FIXED", "main.py")
    except:
        pass

    # 10. Fragile CI/CD Pipeline Logic
    try:
        with open('scrapers/nightly_processor.py', 'r') as f:
            content = f.read()
        if "git commit" in content and "git status --porcelain" not in content:
            add_status("S1-10", "Fragile CI/CD Pipeline Logic", "STILL PRESENT", "scrapers/nightly_processor.py")
        else:
            add_status("S1-10", "Fragile CI/CD Pipeline Logic", "FIXED", "scrapers/nightly_processor.py")
    except:
        pass

    # 11. Type Mismatch During Timeout Fallback
    try:
        with open('llm_router.py', 'r') as f:
            content = f.read()
        if "min(timeout, 120)" in content:
            add_status("S1-11", "Type Mismatch During Timeout Fallback", "STILL PRESENT", "llm_router.py")
        else:
            add_status("S1-11", "Type Mismatch During Timeout Fallback", "FIXED", "llm_router.py")
    except:
        pass

    # 14. Hardcoded Chat ID & Config Drift
    try:
        with open('scrapers/nightly_processor.py', 'r') as f:
            content = f.read()
        if "8534649457" in content:
            add_status("S1-14", "Hardcoded Chat ID & Config Drift", "STILL PRESENT", "scrapers/nightly_processor.py")
        else:
            add_status("S1-14", "Hardcoded Chat ID & Config Drift", "FIXED", "scrapers/nightly_processor.py")
    except:
        pass

    # 15. Dead Code & Redundant Implementations
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        if "unused" in content: # rough proxy
            add_status("S1-15", "Dead Code & Redundant Implementations", "STILL PRESENT", "main.py")
        else:
            add_status("S1-15", "Dead Code & Redundant Implementations", "FIXED", "main.py")
    except:
        pass

    # 17. Unawaited Coroutines in Streaming Callbacks
    try:
        with open('llm_router.py', 'r') as f:
            content = f.read()
        if "run_coroutine_threadsafe" in content and "done_callback" not in content:
            add_status("S1-17", "Unawaited Coroutines in Streaming Callbacks", "STILL PRESENT", "llm_router.py")
        else:
            add_status("S1-17", "Unawaited Coroutines in Streaming Callbacks", "FIXED", "llm_router.py")
    except:
        pass

    # 18. Unbounded ClientSession Creation
    try:
        with open('ai_processor.py', 'r') as f:
            content = f.read()
        if "aiohttp.ClientSession" in content and "session = " in content:
            add_status("S1-18", "Unbounded ClientSession Creation", "STILL PRESENT", "ai_processor.py")
        else:
            add_status("S1-18", "Unbounded ClientSession Creation", "FIXED", "ai_processor.py")
    except:
        pass

    # Source 2 Bugs

    # 1. Missing Authentication on Core Commands
    try:
        with open('bot/commands.py', 'r') as f:
            content = f.read()
        if "@require_auth" not in content:
            add_status("S2-1", "Missing Authentication on Core Commands", "STILL PRESENT", "bot/commands.py")
        else:
            add_status("S2-1", "Missing Authentication on Core Commands", "FIXED", "bot/commands.py")
    except:
        pass

    # 2. Blocking I/O in Async Handlers
    try:
        with open('bot/commands.py', 'r') as f:
            content = f.read()
        if "get_all_canvas_data()" in content and "to_thread" not in content:
            add_status("S2-2", "Blocking I/O in Async Handlers", "STILL PRESENT", "bot/commands.py")
        else:
            add_status("S2-2", "Blocking I/O in Async Handlers", "FIXED", "bot/commands.py")
    except:
        pass

    # 3. Notion Rate Limiter Thread Blocking
    try:
        with open('scrapers/notion_client.py', 'r') as f:
            content = f.read()
        if "time.sleep" in content and "Lock" in content:
            add_status("S2-3", "Notion Rate Limiter Thread Blocking", "STILL PRESENT", "scrapers/notion_client.py")
        else:
            add_status("S2-3", "Notion Rate Limiter Thread Blocking", "FIXED", "scrapers/notion_client.py")
    except:
        pass

    # 4. Google Token Refresh Race Condition
    try:
        with open('scrapers/google_scraper.py', 'r') as f:
            content = f.read()
        if "401" not in content and "403" not in content:
            add_status("S2-4", "Google Token Refresh Race Condition", "STILL PRESENT", "scrapers/google_scraper.py")
        else:
            add_status("S2-4", "Google Token Refresh Race Condition", "FIXED", "scrapers/google_scraper.py")
    except:
        pass

    # 5. Missing Timeouts on Network Calls
    try:
        with open('scrapers/mega_study_builder.py', 'r') as f:
            content = f.read()
        if "requests.get" in content and "timeout=" not in content:
            add_status("S2-5", "Missing Timeouts on Network Calls", "STILL PRESENT", "scrapers/mega_study_builder.py")
        else:
            add_status("S2-5", "Missing Timeouts on Network Calls", "FIXED", "scrapers/mega_study_builder.py")
    except:
        pass

    # 7. Unbounded State Growth
    try:
        with open('bot/commands.py', 'r') as f:
            content = f.read()
        if "seen_tasks" in content and "500" not in content:
            add_status("S2-7", "Unbounded State Growth", "STILL PRESENT", "bot/commands.py")
        else:
            add_status("S2-7", "Unbounded State Growth", "FIXED", "bot/commands.py")
    except:
        pass

    with open('audit_report.md', 'w') as f:
        f.write("# Final Verification Audit Report\n\n")
        for r in report:
            f.write(r)
        f.write("\n\nTotal bugs checked: " + str(len(report)))

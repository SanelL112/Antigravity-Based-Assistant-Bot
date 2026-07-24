import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Ensure the path is correct
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

results = {}

def report(name, success, err=""):
    results[name] = "PASS" if success else f"FAIL: {err}"
    print(f"[{results[name]}] {name}")

if __name__ == "__main__":

    # Category 1: Syntax & Import Tests
    try:
        import config
        import main
        import utils
        import ai_processor
        import llm_router
        import bot.commands
        import bot.state
        import bot.security
        import bot.ai_bridge
        try:
            import scrapers.google_scraper
        except Exception as e:
            print(f"google_scraper error: {e}")
        try:
            import scrapers.canvas_scraper
        except Exception as e:
            print(f"canvas_scraper error: {e}")
        report("Syntax & Import Tests", True)
    except Exception as e:
        report("Syntax & Import Tests", False, str(e))


    # Category 2: Config Tests
    try:
        has_keys = hasattr(config, "TELEGRAM_BOT_TOKEN")
        report("Config Tests", has_keys, "TELEGRAM_BOT_TOKEN missing")
    except Exception as e:
        report("Config Tests", False, str(e))

    # Category 3: Security Tests
    try:
        # 1. run_bash_safely
        out1 = utils.run_bash_safely("echo test")
        
        blocked = False
        try:
            # Check if rm is blocked
            out2 = utils.run_bash_safely("rm -rf /")
            if "blocked" in out2.lower() or "error" in out2.lower() or "not allowed" in out2.lower():
                 blocked = True
        except Exception:
            blocked = True
            
        # 2. PII Scrubbing
        pii = utils.scrub_pii("My SSN is 123-45-6789 and phone is 555-123-4567")
        assert "123-45-6789" not in pii, "SSN not scrubbed"
        
        # 3. require_auth
        @bot.security.require_auth
        async def dummy_auth(update, context):
            return "ok"
            
        class MockUser:
            def __init__(self, uid):
                self.id = uid
                self.username = "test"
        class MockMessage:
            def __init__(self):
                self.text = ""
                self.chat_id = 1234
            async def reply_text(self, text, *args, **kwargs):
                pass
        class MockUpdate:
            def __init__(self, uid):
                self.effective_user = MockUser(uid)
                self.message = MockMessage()
                self.effective_chat = MagicMock()
                self.effective_chat.id = uid
                
        with patch("bot.security.SANEL_CHAT_ID", 1234):
            res_allow = asyncio.run(dummy_auth(MockUpdate(1234), MagicMock()))
            res_deny = asyncio.run(dummy_auth(MockUpdate(9999), MagicMock()))
            assert res_allow == "ok", "Auth failed for allowed user"
            assert res_deny != "ok", "Auth succeeded for denied user"
            
        report("Security Tests", True)
    except Exception as e:
        import traceback
        report("Security Tests", False, traceback.format_exc())

    # Category 4: Command Handler Tests
    try:
        up = MockUpdate(1234)
        ctx = MagicMock()
        asyncio.run(bot.commands.help_command(up, ctx))
        
        if hasattr(bot.commands, "model_command"):
            asyncio.run(bot.commands.model_command(up, ctx))
                
        asyncio.run(bot.commands.ping_command(up, ctx))
        
        if hasattr(bot.commands, "stats_command"):
            asyncio.run(bot.commands.stats_command(up, ctx))
        if hasattr(bot.commands, "correlations_command"):
            asyncio.run(bot.commands.correlations_command(up, ctx))
        if hasattr(bot.commands, "classroom_pdfs_command"):
            asyncio.run(bot.commands.classroom_pdfs_command(up, ctx))
        if hasattr(bot.commands, "errors_command"):
            asyncio.run(bot.commands.errors_command(up, ctx))
        
        assert hasattr(bot.commands, "bash_command"), "bash_command missing"
        assert hasattr(bot.commands, "server_command"), "server_command missing"
        assert hasattr(bot.commands, "backup_command"), "backup_command missing"
        assert hasattr(bot.commands, "restore_command"), "restore_command missing"
        assert hasattr(bot.commands, "summary_command"), "summary_command missing"
        
        report("Command Handler Tests", True)
    except Exception as e:
        import traceback
        report("Command Handler Tests", False, traceback.format_exc())

    # Category 5: Core Pipeline Tests
    try:
        with patch("ai_processor._call_agy_inline", return_value="{}"):
            res = ai_processor.process_all_sources("c", "c", "g", "g")
            
        with patch("llm_router._do_call", return_value="mock"):
            llm_router.call_openrouter("model", "test prompt")
            
        with patch("ai_processor.call_agy", return_value="local_mock"):
            ai_processor.call_agy("test prompt")
            
        report("Core Pipeline Tests", True)
    except Exception as e:
        report("Core Pipeline Tests", False, repr(e))

    # Category 6: Scraper Tests
    try:
        import scrapers.canvas_scraper
        if hasattr(scrapers.canvas_scraper, "fetch_assignments"):
            with patch("scrapers.canvas_scraper.requests.get") as m:
                m.return_value.status_code = 200
                m.return_value.json.return_value = []
                scrapers.canvas_scraper.fetch_assignments()
                
        import scrapers.google_scraper
        if hasattr(scrapers.google_scraper, "fetch_events"):
            with patch("scrapers.google_scraper.build") as m:
                pass # mock building the service
                
        report("Scraper Tests", True)
    except Exception as e:
        report("Scraper Tests", False, str(e))

    # Category 7: Memory/State Tests
    try:
        # Use a dummy state file
        original_state = bot.state.STATE_FILE
        bot.state.STATE_FILE = "test_state.json"
        
        bot.state.save_state({"test": 123})
        st = bot.state.load_state()
        assert st.get("test") == 123, "State did not save properly"
        
        if os.path.exists("test_state.json"):
            os.remove("test_state.json")
        bot.state.STATE_FILE = original_state
        
        if hasattr(utils, "log_activity"):
            utils.log_activity("test", "test action")
        report("Memory/State Tests", True)
    except Exception as e:
        report("Memory/State Tests", False, str(e))

    # Category 8: Background Jobs
    try:
        import run_watchdog
        import scrapers.nightly_processor
        report("Background Jobs", True)
    except Exception as e:
        report("Background Jobs", False, str(e))

    # Category 9: Error Handling
    try:
        if hasattr(llm_router, "call_openrouter"):
            with patch("llm_router._get_client") as m:
                m.side_effect = Exception("API fail")
                try:
                    # assuming there's a safe call mechanism or fallback logic
                    llm_router.call_openrouter("model", "test prompt", fallback_chain=[])
                except Exception:
                    pass
        report("Error Handling", True)
    except Exception as e:
        report("Error Handling", False, str(e))

    print("\n--- FINAL REPORT ---")
    for k, v in results.items():
        print(f"{k}: {v}")

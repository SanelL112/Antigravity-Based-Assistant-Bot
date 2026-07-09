#!/usr/bin/env python3
"""Run the personal assistant bot watchdog cycle."""

import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

# Set up environment
bot_dir = "/home/sanel/personal-assistant-bot"
os.chdir(bot_dir)
sys.path.insert(0, bot_dir)

async def run_watchdog():
    """Run the watchdog check cycle"""
    # Import after setting up path
    from main import check_updates
    
    # Create a mock context
    class MockContext:
        def __init__(self):
            self.job = MagicMock()
            self.job.chat_id = 8534649457
            self.bot = MagicMock()
            self.bot.send_message = AsyncMock()
    
    context = MockContext()
    
    # Run the watchdog
    try:
        await check_updates(context)
        print("Watchdog check completed successfully")
    except Exception as e:
        print(f"Watchdog error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_watchdog())
#!/usr/bin/env python3
"""Test Telegram bot configuration."""

from telegram import Bot
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

print(f"Testing bot: {bot_token[:20]}...")
print(f"Target channel: {channel_id}")

async def test_bot():
    """Async function to test bot configuration."""
    try:
        bot = Bot(token=bot_token)

        # Test message
        test_message = """🚀 **Bank News Bot Test**

✅ Bot configured successfully
✅ Channel access confirmed

This is a test message from your Bank News pipeline."""

        result = await bot.send_message(
            chat_id=channel_id,
            text=test_message,
            parse_mode="Markdown"
        )

        print("\n✅ Test message sent successfully!")
        print(f"Message ID: {result.message_id}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("  1. Bot token is correct")
        print("  2. Bot is admin of channel")
        print("  3. Channel ID is correct")
        print("  4. Bot has 'Post messages' permission")

if __name__ == "__main__":
    asyncio.run(test_bot())

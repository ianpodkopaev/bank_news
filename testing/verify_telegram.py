#!/usr/bin/env python3
"""Verify Telegram bot permissions and channel access."""

from telegram import Bot
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

async def verify_access():
    """Verify bot has access to channel."""
    print(f"Bot token: {bot_token[:20]}...")
    print(f"Channel ID: {channel_id}\n")

    try:
        bot = Bot(token=bot_token)

        # Test 1: Try to get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot name: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}\n")

        # Test 2: Try to get channel info
        print("Testing channel access...")
        try:
            chat = await bot.get_chat(chat_id=channel_id)
            print(f"✅ Channel found: {chat.title}")
            print(f"✅ Channel type: {chat.type}")
            print(f"✅ Channel ID: {chat.id}")

            # Test 3: Check if bot is member/admin
            print("\nChecking bot permissions...")
            try:
                members = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)
                print(f"✅ Bot is member: {members.status}")
                print(f"   Permissions:")
                print(f"   - Can post messages: {members.can_post_messages}")
                print(f"   - Can edit messages: {members.can_edit_messages}")
                print(f"   - Can delete messages: {members.can_delete_messages}")
                print(f"   - Is admin: {members.status == 'administrator'}")

                if not members.can_post_messages:
                    print("\n❌ ERROR: Bot cannot post messages!")
                    print("   Please make bot an administrator in channel settings")
                elif members.status != 'administrator':
                    print("\n⚠️  WARNING: Bot is not an administrator")
                    print("   Some features may not work")
                else:
                    print("\n✅ SUCCESS: Bot is properly configured!")

            except Exception as e:
                print(f"\n❌ Cannot check membership: {e}")
                print("   Bot may not be in the channel")

        except Exception as e:
            print(f"❌ ERROR: Cannot access channel: {e}")
            print("\nPossible causes:")
            print("  1. Channel ID is incorrect")
            print("  2. Bot is not added to the channel")
            print("  3. Bot is not an admin of the channel")
            print("\nTo get correct channel ID:")
            print("  1. Forward a message from your channel to @GetChannelIdBot")
            print("  2. Update TELEGRAM_CHANNEL_ID in .env")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("Please check your bot token")

if __name__ == "__main__":
    asyncio.run(verify_access())

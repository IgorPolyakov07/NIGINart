import asyncio
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from telethon import TelegramClient
from src.config.settings import get_settings
async def main():
    settings = get_settings()
    print("=" * 60)
    print("Telegram Session Initialization")
    print("=" * 60)
    print(f"\nAPI ID: {settings.telegram_api_id}")
    print(f"Session file: {settings.telegram_session_file}.session")
    print("\nYou will be prompted to:")
    print("  1. Enter your phone number (with country code)")
    print("  2. Enter the verification code from Telegram")
    print("  3. Enter your 2FA password (if enabled)")
    print("\n" + "=" * 60 + "\n")
    client = TelegramClient(
        settings.telegram_session_file,
        settings.telegram_api_id,
        settings.telegram_api_hash,
        timeout=settings.api_timeout_seconds
    )
    try:
        await client.start()
        me = await client.get_me()
        print("\n" + "=" * 60)
        print("✅ Telegram session initialized successfully!")
        print("=" * 60)
        print(f"\nLogged in as:")
        print(f"  Name: {me.first_name} {me.last_name or ''}")
        print(f"  Username: @{me.username}" if me.username else "  Username: (not set)")
        print(f"  Phone: {me.phone}")
        print(f"\nSession file created: {settings.telegram_session_file}.session")
        print("\nYou can now use TelegramParser without re-authenticating.")
        print("=" * 60 + "\n")
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ Authentication failed!")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nPlease check:")
        print("  1. TELEGRAM_API_ID and TELEGRAM_API_HASH are correct in .env")
        print("  2. Phone number includes country code (e.g., +1234567890)")
        print("  3. Verification code is entered within time limit")
        print("=" * 60 + "\n")
        raise
    finally:
        await client.disconnect()
if __name__ == '__main__':
    asyncio.run(main())

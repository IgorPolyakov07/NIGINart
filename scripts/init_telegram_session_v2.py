import asyncio
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from telethon import TelegramClient
from telethon.sessions import StringSession
from src.config.settings import get_settings
async def main():
    settings = get_settings()
    print("=" * 60)
    print("Telegram Session Initialization v2")
    print("=" * 60)
    print(f"API ID: {settings.telegram_api_id}")
    print(f"API Hash: {settings.telegram_api_hash[:8]}...")
    print("=" * 60)
    client = TelegramClient(
        settings.telegram_session_file,
        settings.telegram_api_id,
        settings.telegram_api_hash,
        device_model="Desktop",
        system_version="Windows 10",
        app_version="4.16.8",
        lang_code="ru",
        system_lang_code="ru-RU"
    )
    print("\nConnecting to Telegram...")
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\nAlready authorized as: {me.first_name} (@{me.username})")
        await client.disconnect()
        return
    print("\nNot authorized. Starting authentication...")
    phone = input("\nEnter phone number (with +7 or country code): ").strip()
    print(f"\nSending code request to {phone}...")
    try:
        sent = await client.send_code_request(phone)
        print(f"Code sent! Type: {sent.type}")
        print(f"Phone code hash: {sent.phone_code_hash[:10]}...")
        code = input("\nEnter the code from Telegram: ").strip()
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "Two-steps verification" in str(e) or "2FA" in str(e).upper():
                password = input("\nEnter 2FA password: ").strip()
                await client.sign_in(password=password)
            else:
                raise
        me = await client.get_me()
        print(f"\nSuccess! Logged in as: {me.first_name} (@{me.username})")
        print(f"Session file created: {settings.telegram_session_file}.session")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from telethon import TelegramClient
from telethon.tl.functions.auth import ResendCodeRequest, SendCodeRequest
from telethon.tl.types import (
    CodeSettings,
    SentCodeTypeApp,
    SentCodeTypeSms,
    SentCodeTypeCall,
    SentCodeTypeFlashCall,
    SentCodeTypeMissedCall,
)
from src.config.settings import get_settings
def describe_code_type(sent_code):
    code_type = sent_code.type
    if isinstance(code_type, SentCodeTypeApp):
        return f"APP (in-app message, {code_type.length} digits)"
    elif isinstance(code_type, SentCodeTypeSms):
        return f"SMS ({code_type.length} digits)"
    elif isinstance(code_type, SentCodeTypeCall):
        return f"VOICE CALL ({code_type.length} digits)"
    elif isinstance(code_type, SentCodeTypeFlashCall):
        return f"FLASH CALL (pattern: {code_type.pattern})"
    elif isinstance(code_type, SentCodeTypeMissedCall):
        return f"MISSED CALL (last {code_type.length} digits of calling number)"
    else:
        return f"UNKNOWN: {type(code_type).__name__}"
async def main():
    settings = get_settings()
    print("=" * 60)
    print("Telegram Session Initialization v3")
    print("=" * 60)
    print(f"API ID: {settings.telegram_api_id}")
    print("=" * 60)
    client = TelegramClient(
        settings.telegram_session_file,
        settings.telegram_api_id,
        settings.telegram_api_hash,
        device_model="Telegram Desktop",
        system_version="Windows 10 x64",
        app_version="4.16.8 x64",
        lang_code="ru",
        system_lang_code="ru-RU"
    )
    await client.connect()
    print("Connected to Telegram servers.")
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\nAlready authorized as: {me.first_name} (@{me.username})")
        await client.disconnect()
        return
    phone = input("\nEnter phone number (e.g. +79221755080): ").strip()
    print(f"\nSending code to {phone}...")
    try:
        sent_code = await client.send_code_request(phone)
    except Exception as e:
        print(f"Error sending code: {e}")
        await client.disconnect()
        return
    phone_code_hash = sent_code.phone_code_hash
    print(f"\n>>> Code delivery method: {describe_code_type(sent_code)}")
    print(f">>> Phone code hash: {phone_code_hash[:16]}...")
    if sent_code.next_type:
        print(f">>> Next available method: {sent_code.next_type}")
    if sent_code.timeout:
        print(f">>> Can request resend in: {sent_code.timeout} seconds")
    while True:
        print("\n" + "-" * 40)
        print("Options:")
        print("  1. Enter code (if you received it)")
        print("  2. Resend code (request again)")
        print("  3. Request code via PHONE CALL")
        print("  4. Cancel and exit")
        print("-" * 40)
        choice = input("Choose option (1-4): ").strip()
        if choice == "1":
            code = input("Enter the code: ").strip()
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                break
            except Exception as e:
                error_str = str(e)
                if "SESSION_PASSWORD_NEEDED" in error_str or "2FA" in error_str.upper():
                    print("\n2FA is enabled. Enter your password:")
                    password = input("Password: ").strip()
                    try:
                        await client.sign_in(password=password)
                        break
                    except Exception as e2:
                        print(f"2FA Error: {e2}")
                elif "PHONE_CODE_INVALID" in error_str:
                    print("Invalid code! Try again.")
                elif "PHONE_CODE_EXPIRED" in error_str:
                    print("Code expired! Request a new one (option 2 or 3).")
                else:
                    print(f"Error: {e}")
        elif choice == "2":
            print("\nResending code...")
            try:
                sent_code = await client(ResendCodeRequest(phone, phone_code_hash))
                phone_code_hash = sent_code.phone_code_hash
                print(f">>> New delivery method: {describe_code_type(sent_code)}")
            except Exception as e:
                print(f"Resend error: {e}")
        elif choice == "3":
            print("\nRequesting phone call...")
            try:
                result = await client(SendCodeRequest(
                    phone_number=phone,
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    settings=CodeSettings(
                        allow_flashcall=False,
                        current_number=True,
                        allow_app_hash=False,
                        allow_missed_call=False,
                        allow_firebase=False,
                    )
                ))
                phone_code_hash = result.phone_code_hash
                print(f">>> Delivery method: {describe_code_type(result)}")
                print("Wait for the phone call...")
            except Exception as e:
                error_msg = str(e)
                if "PHONE_CODE_EXPIRED" in error_msg:
                    try:
                        sent_code = await client(ResendCodeRequest(phone, phone_code_hash))
                        phone_code_hash = sent_code.phone_code_hash
                        print(f">>> Resent. Delivery method: {describe_code_type(sent_code)}")
                    except Exception as e2:
                        print(f"Error: {e2}")
                else:
                    print(f"Call request error: {e}")
        elif choice == "4":
            print("Cancelled.")
            await client.disconnect()
            return
        else:
            print("Invalid option.")
    me = await client.get_me()
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"Logged in as: {me.first_name} {me.last_name or ''}")
    print(f"Username: @{me.username}" if me.username else "Username: not set")
    print(f"Phone: {me.phone}")
    print(f"\nSession file: {settings.telegram_session_file}.session")
    print("=" * 60)
    await client.disconnect()
if __name__ == "__main__":
    asyncio.run(main())

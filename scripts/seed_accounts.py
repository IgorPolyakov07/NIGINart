import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.config.settings import get_settings
from src.models.account import Account
settings = get_settings()
ACCOUNTS = [
    {
        "platform": "instagram",
        "account_id": "niginart.brand",
        "account_url": "https://www.instagram.com/niginart.brand",
        "display_name": "NIGINart Brand (Instagram)",
        "is_active": True,
    },
    {
        "platform": "instagram",
        "account_id": "niginart_official",
        "account_url": "https://www.instagram.com/niginart_official",
        "display_name": "NIGINart Official (Instagram)",
        "is_active": True,
    },
    {
        "platform": "instagram",
        "account_id": "niginart_brand",
        "account_url": "https://www.instagram.com/niginart_brand",
        "display_name": "NIGINart Brand Alt (Instagram)",
        "is_active": True,
    },
    {
        "platform": "telegram",
        "account_id": "NIGINart_official",
        "account_url": "https://t.me/NIGINart_official",
        "display_name": "NIGINart Official (Telegram)",
        "is_active": True,
    },
    {
        "platform": "dzen",
        "account_id": "68d24f523b89f667f57816e2",
        "account_url": "https://dzen.ru/id/68d24f523b89f667f57816e2",
        "display_name": "NIGINart (Яндекс Дзен)",
        "is_active": True,
    },
    {
        "platform": "pinterest",
        "account_id": "2AruYuDfT",
        "account_url": "https://pin.it/2AruYuDfT",
        "display_name": "NIGINart (Pinterest)",
        "is_active": True,
    },
    {
        "platform": "youtube",
        "account_id": "UC8Qu8iMjh8nSNMYoBWHReAA",
        "account_url": "https://www.youtube.com/channel/UC8Qu8iMjh8nSNMYoBWHReAA",
        "display_name": "NIGINart (YouTube)",
        "is_active": True,
    },
    {
        "platform": "tiktok",
        "account_id": "niginart_brand",
        "account_url": "https://www.tiktok.com/@niginart_brand",
        "display_name": "NIGINart Brand (TikTok)",
        "is_active": True,
    },
    {
        "platform": "wibes",
        "account_id": "288449",
        "account_url": "https://wibes.ru/author/288449",
        "display_name": "NIGINart (Wibes)",
        "is_active": True,
    },
    {
        "platform": "vk",
        "account_id": "niginart_official",
        "account_url": "https://vk.com/niginart_official",
        "display_name": "NIGINart Official (VK)",
        "is_active": True,
    },
]
async def seed_accounts() -> None:
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        print("🌱 Seeding accounts...")
        for account_data in ACCOUNTS:
            account = Account(**account_data)
            session.add(account)
            print(f"  ✅ Added: {account.display_name}")
        await session.commit()
        print(f"\n✨ Successfully seeded {len(ACCOUNTS)} accounts!")
    await engine.dispose()
if __name__ == "__main__":
    asyncio.run(seed_accounts())

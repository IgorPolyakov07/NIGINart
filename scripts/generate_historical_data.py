import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import get_settings
from src.models.account import Account
from src.models.metric import Metric
settings = get_settings()
async def generate_historical_data(days: int = 30):
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(
            select(Account).where(Account.is_active == True)
        )
        accounts = result.scalars().all()
        print(f"Found {len(accounts)} active accounts")
        for account in accounts:
            print(f"\nGenerating data for {account.display_name} ({account.platform})...")
            base_followers = random.randint(10000, 100000)
            base_posts = random.randint(50, 200)
            for day_offset in range(days, 0, -1):
                collected_at = datetime.utcnow() - timedelta(days=day_offset)
                collected_at += timedelta(hours=random.randint(0, 23),
                                         minutes=random.randint(0, 59))
                growth_factor = 1 + (days - day_offset) / days * 0.3
                daily_variation = random.uniform(0.95, 1.05)
                followers = int(base_followers * growth_factor * daily_variation)
                posts_count = int(base_posts * growth_factor * daily_variation)
                total_views = followers * random.randint(3, 10)
                total_likes = int(total_views * random.uniform(0.03, 0.08))
                total_comments = int(total_views * random.uniform(0.005, 0.02))
                total_shares = int(total_views * random.uniform(0.01, 0.03))
                engagement_rate = (total_likes + total_comments) / max(total_views, 1) * 100
                extra_data = {}
                if account.platform == "youtube":
                    extra_data = {
                        "channel_id": account.account_id,
                        "video_count": posts_count,
                        "total_watch_time_hours": random.randint(1000, 50000),
                        "avg_view_duration": random.randint(120, 600),
                        "recent_videos": []
                    }
                elif account.platform == "telegram":
                    extra_data = {
                        "channel_username": account.account_id,
                        "avg_views": int(total_views / max(posts_count, 1)),
                        "err_views": round(engagement_rate, 2)
                    }
                elif account.platform == "instagram":
                    extra_data = {
                        "username": account.account_id,
                        "avg_likes_per_post": int(total_likes / max(posts_count, 1)),
                        "avg_comments_per_post": int(total_comments / max(posts_count, 1))
                    }
                elif account.platform == "tiktok":
                    extra_data = {
                        "username": account.account_id,
                        "total_video_views": total_views,
                        "avg_video_views": int(total_views / max(posts_count, 1))
                    }
                elif account.platform == "vk":
                    extra_data = {
                        "screen_name": account.account_id,
                        "wall_count": posts_count
                    }
                metric = Metric(
                    id=uuid4(),
                    account_id=account.id,
                    collected_at=collected_at,
                    followers=followers,
                    posts_count=posts_count,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    total_views=total_views,
                    total_shares=total_shares,
                    engagement_rate=round(engagement_rate, 2),
                    extra_data=extra_data
                )
                session.add(metric)
            print(f"  Generated {days} days of data for {account.display_name}")
        await session.commit()
        print(f"\n✅ Successfully generated historical data for {len(accounts)} accounts!")
        print(f"   Period: {days} days back from today")
    await engine.dispose()
if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"🕒 Generating {days} days of historical metrics data...")
    asyncio.run(generate_historical_data(days))
    print("\n✨ Done!")

import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import get_settings
from src.models.account import Account
from src.models.metric import Metric
settings = get_settings()
def generate_realistic_videos(base_date: datetime, num_videos: int = 10) -> List[Dict[str, Any]]:
    title_templates = [
        "трикотажный костюм на молнии {code}",
        "велюровый костюм женский спортивный {code}",
        "спортивный костюм на молнии {code}",
        "тёплый спортивный костюм с начесом {code}",
        "брючный костюм приталенный {code}",
        "Замшевый брючный костюм {code}",
        "тёплый спортивный костюм на молнии с начесом {code}",
        "замшевый брючный костюм {code}",
        "велюровый женский костюм {code}",
        "спортивный костюм с начесом {code}"
    ]
    videos = []
    for i in range(num_videos):
        days_back = random.randint(0, 14)
        hours_back = random.randint(0, 23)
        video_date = base_date - timedelta(days=days_back, hours=hours_back)
        code = f"{random.randint(100000, 999999)}{random.randint(100, 999)}"
        title = random.choice(title_templates).format(code=code)
        if random.random() > 0.5:
            title += " #шопинг #женскаяодежда"
        video_age_days = (base_date - video_date).days
        base_views = random.randint(100, 2000)
        if video_age_days > 7:
            base_views *= random.randint(2, 5)
        elif video_age_days > 3:
            base_views *= random.randint(1, 3)
        views = base_views
        likes = int(views * random.uniform(0.003, 0.015))
        comments = int(views * random.uniform(0.0001, 0.001))
        videos.append({
            "video_id": f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=11))}",
            "title": title,
            "published_at": video_date.isoformat().replace('+00:00', 'Z'),
            "views": views,
            "likes": likes,
            "comments": comments
        })
    videos.sort(key=lambda x: x['published_at'], reverse=True)
    return videos
async def generate_youtube_historical_data(days: int = 30):
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(
            select(Account).where(Account.platform == 'youtube', Account.is_active == True)
        )
        accounts = result.scalars().all()
        if not accounts:
            print("No YouTube accounts found!")
            return
        print(f"Found {len(accounts)} YouTube account(s)")
        for account in accounts:
            print(f"\nGenerating data for {account.display_name}...")
            current_subscribers = 56
            current_videos = 226
            start_subscribers = int(current_subscribers / 1.1)
            start_videos = current_videos - random.randint(5, 10)
            for day_offset in range(days, 0, -1):
                collected_at = datetime.utcnow() - timedelta(days=day_offset)
                collected_at += timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                progress = (days - day_offset) / days
                growth_trend = start_subscribers + (current_subscribers - start_subscribers) * progress
                daily_noise = random.uniform(-1, 1)
                subscribers = max(start_subscribers, int(growth_trend + daily_noise))
                videos_trend = start_videos + (current_videos - start_videos) * progress
                videos_noise = random.uniform(-0.5, 0.5)
                videos_count = max(start_videos, int(videos_trend + videos_noise))
                recent_videos = generate_realistic_videos(collected_at, num_videos=10)
                total_views = sum(v['views'] for v in recent_videos) * random.randint(5, 10)
                total_likes = sum(v['likes'] for v in recent_videos) * random.randint(5, 10)
                total_comments = sum(v['comments'] for v in recent_videos) * random.randint(5, 10)
                total_shares = int(total_views * random.uniform(0.005, 0.015))
                engagement_rate = (total_likes + total_comments) / max(total_views, 1) * 100
                avg_views = int(sum(v['views'] for v in recent_videos) / len(recent_videos)) if recent_videos else 0
                avg_likes = int(sum(v['likes'] for v in recent_videos) / len(recent_videos)) if recent_videos else 0
                avg_comments = int(sum(v['comments'] for v in recent_videos) / len(recent_videos)) if recent_videos else 0
                total_recent_views = sum(v['views'] for v in recent_videos)
                total_recent_likes = sum(v['likes'] for v in recent_videos)
                total_recent_comments = sum(v['comments'] for v in recent_videos)
                best_video = max(recent_videos, key=lambda v: v['views']) if recent_videos else None
                extra_data = {
                    "channel_id": account.account_id,
                    "recent_videos": recent_videos,
                    "metrics_7d": {
                        "videos_count": len(recent_videos),
                        "total_views": total_recent_views,
                        "total_likes": total_recent_likes,
                        "total_comments": total_recent_comments,
                        "avg_views_per_video": avg_views,
                        "engagement_rate": round((total_recent_likes + total_recent_comments) / max(total_recent_views, 1) * 100, 2),
                        "best_video": {
                            "video_id": best_video['video_id'],
                            "title": best_video['title'],
                            "views": best_video['views'],
                            "likes": best_video['likes']
                        } if best_video else None
                    },
                    "metrics_30d": {
                        "videos_count": len(recent_videos),
                        "total_views": total_recent_views,
                        "total_likes": total_recent_likes,
                        "total_comments": total_recent_comments,
                        "avg_views_per_video": avg_views,
                        "avg_likes_per_video": avg_likes,
                        "avg_comments_per_video": avg_comments,
                        "engagement_rate": round((total_recent_likes + total_recent_comments) / max(total_recent_views, 1) * 100, 2),
                        "best_video": {
                            "video_id": best_video['video_id'],
                            "title": best_video['title'],
                            "views": best_video['views'],
                            "likes": best_video['likes']
                        } if best_video else None
                    },
                    "metrics_90d": {
                        "videos_count": len(recent_videos),
                        "total_views": total_recent_views,
                        "total_likes": total_recent_likes,
                        "total_comments": total_recent_comments,
                        "avg_views_per_video": avg_views,
                        "engagement_rate": round((total_recent_likes + total_recent_comments) / max(total_recent_views, 1) * 100, 2),
                        "best_video": {
                            "video_id": best_video['video_id'],
                            "title": best_video['title'],
                            "views": best_video['views'],
                            "likes": best_video['likes']
                        } if best_video else None
                    }
                }
                metric = Metric(
                    id=uuid4(),
                    account_id=account.id,
                    collected_at=collected_at,
                    followers=subscribers,
                    posts_count=videos_count,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    total_views=total_views,
                    total_shares=total_shares,
                    engagement_rate=round(engagement_rate, 2),
                    extra_data=extra_data
                )
                session.add(metric)
            print(f"  Generated {days} days of data with video information")
        await session.commit()
        print(f"\n✅ Successfully generated YouTube historical data!")
        print(f"   Period: {days} days")
        print(f"   Each metric includes 10 recent videos with realistic stats")
    await engine.dispose()
if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"🎬 Generating {days} days of YouTube metrics with video data...")
    asyncio.run(generate_youtube_historical_data(days))
    print("\n✨ Done!")

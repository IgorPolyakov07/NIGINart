import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.parsers.youtube_parser import YouTubeParser
async def main():
    parser = YouTubeParser(
        account_id='UC8Qu8iMjh8nSNMYoBWHReAA',
        account_url='https://www.youtube.com/channel/UC8Qu8iMjh8nSNMYoBWHReAA'
    )
    print("Checking if YouTube API is available...")
    if not await parser.is_available():
        print("ERROR: YouTube parser not available. Check API key.")
        return
    print("Fetching real metrics from YouTube API...\n")
    try:
        metrics = await parser.fetch_metrics()
        print("=" * 60)
        print("РЕАЛЬНЫЕ МЕТРИКИ КАНАЛА @NIGINart_official_01")
        print("=" * 60)
        print(f"Подписчики (Subscribers):  {metrics.followers:,}")
        print(f"Всего видео (Total Videos): {metrics.posts_count:,}")
        print(f"Просмотры (Total Views):    {metrics.total_views:,}")
        print(f"Лайки (Total Likes):        {metrics.total_likes:,}")
        print(f"Комментарии (Comments):     {metrics.total_comments:,}")
        print(f"Вовлеченность (Engagement): {metrics.engagement_rate:.2f}%")
        print("=" * 60)
        if metrics.extra_data:
            print("\nДополнительная информация:")
            if 'recent_videos' in metrics.extra_data:
                print(f"  - Последних видео: {len(metrics.extra_data['recent_videos'])}")
            if 'metrics_30d' in metrics.extra_data:
                m30 = metrics.extra_data['metrics_30d']
                print(f"\nМетрики за 30 дней:")
                print(f"  - Средние просмотры на видео: {m30.get('avg_views_per_video', 'N/A')}")
                print(f"  - Средние лайки на видео: {m30.get('avg_likes_per_video', 'N/A')}")
        print("\n✅ Данные успешно получены!")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.parsers.youtube_parser import YouTubeParser
async def main():
    parser = YouTubeParser(
        account_id='UC8Qu8iMjh8nSNMYoBWHReAA',
        account_url='https://www.youtube.com/channel/UC8Qu8iMjh8nSNMYoBWHReAA'
    )
    print("Checking YouTube API availability...")
    if not await parser.is_available():
        print("ERROR: YouTube parser not available. Check API key.")
        return
    print("Fetching all recent videos from channel...")
    try:
        all_videos = parser._get_all_recent_videos(max_results=50)
        print(f"\n✅ Successfully fetched {len(all_videos)} videos")
        print("=" * 80)
        video_data = []
        for i, video in enumerate(all_videos, 1):
            video_data.append({
                "video_id": video['video_id'],
                "title": video['title'],
                "published_at": video['published_at'].isoformat() if hasattr(video['published_at'], 'isoformat') else str(video['published_at']),
                "views": video['views'],
                "likes": video['likes'],
                "comments": video['comments']
            })
            print(f"{i}. {video['video_id']} | {video['title'][:60]}...")
        print("=" * 80)
        output_file = "scripts/real_youtube_video_ids.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved {len(video_data)} video IDs to {output_file}")
        print("\nThese REAL video_ids can now be used in generate_youtube_history.py!")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    asyncio.run(main())

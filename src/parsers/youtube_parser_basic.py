from datetime import datetime, timedelta
from typing import Optional
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class YouTubeParser(BaseParser):
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self.youtube = None
    def get_platform_name(self) -> str:
        return "youtube"
    def _init_client(self) -> None:
        if self.youtube is None:
            self.youtube = build(
                'youtube',
                'v3',
                developerKey=settings.youtube_api_key,
                cache_discovery=False
            )
            logger.debug("YouTube API client initialized")
    async def is_available(self) -> bool:
        try:
            self._init_client()
            self.youtube.channels().list(
                part='id',
                id=self.account_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"YouTube availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        self._init_client()
        async def _fetch() -> PlatformMetrics:
            channel_response = self.youtube.channels().list(
                part='statistics,snippet',
                id=self.account_id
            ).execute()
            if not channel_response.get('items'):
                raise ValueError(f"Channel {self.account_id} not found")
            channel = channel_response['items'][0]
            stats = channel['statistics']
            snippet = channel['snippet']
            subscribers = int(stats.get('subscriberCount', 0))
            video_count = int(stats.get('videoCount', 0))
            total_views = int(stats.get('viewCount', 0))
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
            search_response = self.youtube.search().list(
                part='id',
                channelId=self.account_id,
                type='video',
                publishedAfter=thirty_days_ago,
                maxResults=50,
                order='date'
            ).execute()
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            total_likes = 0
            total_comments = 0
            recent_views = 0
            if video_ids:
                videos_response = self.youtube.videos().list(
                    part='statistics',
                    id=','.join(video_ids)
                ).execute()
                for video in videos_response.get('items', []):
                    vstats = video['statistics']
                    total_likes += int(vstats.get('likeCount', 0))
                    total_comments += int(vstats.get('commentCount', 0))
                    recent_views += int(vstats.get('viewCount', 0))
            engagement = total_likes + total_comments
            engagement_rate = (engagement / recent_views * 100) if recent_views > 0 else 0.0
            return PlatformMetrics(
                platform=self.get_platform_name(),
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=subscribers,
                posts_count=video_count,
                total_views=total_views,
                total_likes=total_likes,
                total_comments=total_comments,
                engagement_rate=round(engagement_rate, 2),
                extra_data={
                    "channel_title": snippet.get('title'),
                    "recent_videos_count": len(video_ids),
                    "recent_views_30d": recent_views,
                    "avg_likes_per_video": round(total_likes / len(video_ids), 2) if video_ids else 0
                }
            )
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay,
            exceptions=(HttpError, ConnectionError, TimeoutError)
        )

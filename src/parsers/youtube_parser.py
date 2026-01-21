from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
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
    def _get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        if not video_ids:
            return []
        videos_response = self.youtube.videos().list(
            part='statistics,snippet',
            id=','.join(video_ids),
            fields='items(id,snippet(title,publishedAt),statistics(viewCount,likeCount,commentCount))'
        ).execute()
        video_details = []
        for video in videos_response.get('items', []):
            vstats = video.get('statistics', {})
            snippet = video.get('snippet', {})
            published_at_str = snippet.get('publishedAt', '')
            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                published_at = datetime.utcnow().replace(tzinfo=timezone.utc)
            video_details.append({
                'video_id': video['id'],
                'title': snippet.get('title', 'Unknown'),
                'published_at': published_at,
                'views': int(vstats.get('viewCount', 0)),
                'likes': int(vstats.get('likeCount', 0)),
                'comments': int(vstats.get('commentCount', 0))
            })
        return video_details
    def _calculate_video_metrics(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not videos:
            return {
                'total_videos': 0,
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0,
                'avg_views': 0,
                'avg_likes': 0,
                'avg_comments': 0,
                'best_video': None,
                'engagement_rate': 0.0
            }
        total_views = sum(v['views'] for v in videos)
        total_likes = sum(v['likes'] for v in videos)
        total_comments = sum(v['comments'] for v in videos)
        count = len(videos)
        best_video = max(videos, key=lambda v: v['views'])
        engagement = total_likes + total_comments
        engagement_rate = (engagement / total_views * 100) if total_views > 0 else 0.0
        return {
            'total_videos': count,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views': round(total_views / count, 2),
            'avg_likes': round(total_likes / count, 2),
            'avg_comments': round(total_comments / count, 2),
            'best_video': {
                'title': best_video['title'],
                'views': best_video['views'],
                'likes': best_video['likes'],
                'video_id': best_video['video_id']
            },
            'engagement_rate': round(engagement_rate, 2)
        }
    def _get_all_recent_videos(self, max_results: int = 50) -> List[Dict[str, Any]]:
        search_response = self.youtube.search().list(
            part='id',
            channelId=self.account_id,
            type='video',
            maxResults=max_results,
            order='date',
            fields='items(id(videoId))'
        ).execute()
        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        if not video_ids:
            return []
        return self._get_video_details(video_ids)
    def _filter_videos_by_days(self, videos: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
        cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=days)
        return [v for v in videos if v['published_at'] >= cutoff_date]
    async def fetch_metrics(self) -> PlatformMetrics:
        self._init_client()
        async def _fetch() -> PlatformMetrics:
            channel_response = self.youtube.channels().list(
                part='statistics,snippet',
                id=self.account_id,
                fields='items(snippet(title,description,publishedAt),statistics(subscriberCount,videoCount,viewCount))'
            ).execute()
            if not channel_response.get('items'):
                raise ValueError(f"Channel {self.account_id} not found")
            channel = channel_response['items'][0]
            stats = channel['statistics']
            snippet = channel['snippet']
            subscribers = int(stats.get('subscriberCount', 0))
            video_count = int(stats.get('videoCount', 0))
            total_views = int(stats.get('viewCount', 0))
            logger.info(f"Fetching recent videos for channel {self.account_id}")
            all_videos = self._get_all_recent_videos(max_results=50)
            videos_7d = self._filter_videos_by_days(all_videos, 7)
            videos_30d = self._filter_videos_by_days(all_videos, 30)
            videos_90d = self._filter_videos_by_days(all_videos, 90)
            logger.debug(f"Videos fetched: 7d={len(videos_7d)}, 30d={len(videos_30d)}, 90d={len(videos_90d)}")
            metrics_7d = self._calculate_video_metrics(videos_7d)
            metrics_30d = self._calculate_video_metrics(videos_30d)
            metrics_90d = self._calculate_video_metrics(videos_90d)
            all_time_top = {
                'best_video': metrics_90d.get('best_video'),
                'avg_views_top50': metrics_90d.get('avg_views', 0),
                'total_views_top50': metrics_90d.get('total_views', 0)
            }
            return PlatformMetrics(
                platform=self.get_platform_name(),
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=subscribers,
                posts_count=video_count,
                total_views=total_views,
                total_likes=metrics_30d['total_likes'],
                total_comments=metrics_30d['total_comments'],
                engagement_rate=metrics_30d['engagement_rate'],
                extra_data={
                    "channel_title": snippet.get('title'),
                    "channel_description": snippet.get('description', '')[:200],
                    "channel_created_at": snippet.get('publishedAt'),
                    "metrics_7d": {
                        "videos_count": metrics_7d['total_videos'],
                        "total_views": metrics_7d['total_views'],
                        "total_likes": metrics_7d['total_likes'],
                        "total_comments": metrics_7d['total_comments'],
                        "avg_views_per_video": metrics_7d['avg_views'],
                        "engagement_rate": metrics_7d['engagement_rate'],
                        "best_video": metrics_7d.get('best_video')
                    },
                    "metrics_30d": {
                        "videos_count": metrics_30d['total_videos'],
                        "total_views": metrics_30d['total_views'],
                        "total_likes": metrics_30d['total_likes'],
                        "total_comments": metrics_30d['total_comments'],
                        "avg_views_per_video": metrics_30d['avg_views'],
                        "avg_likes_per_video": metrics_30d['avg_likes'],
                        "avg_comments_per_video": metrics_30d['avg_comments'],
                        "engagement_rate": metrics_30d['engagement_rate'],
                        "best_video": metrics_30d.get('best_video')
                    },
                    "metrics_90d": {
                        "videos_count": metrics_90d['total_videos'],
                        "total_views": metrics_90d['total_views'],
                        "total_likes": metrics_90d['total_likes'],
                        "total_comments": metrics_90d['total_comments'],
                        "avg_views_per_video": metrics_90d['avg_views'],
                        "engagement_rate": metrics_90d['engagement_rate'],
                        "best_video": metrics_90d.get('best_video')
                    },
                    "all_time_top_videos": all_time_top,
                    "recent_videos": [
                        {
                            "title": v['title'],
                            "views": v['views'],
                            "likes": v['likes'],
                            "comments": v['comments'],
                            "published_at": v['published_at'].isoformat() if isinstance(v['published_at'], datetime) else v['published_at'],
                            "video_id": v['video_id']
                        }
                        for v in videos_30d[:10]
                    ]
                }
            )
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay,
            exceptions=(HttpError, ConnectionError, TimeoutError)
        )
    async def close(self) -> None:
        pass

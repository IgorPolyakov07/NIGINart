from datetime import datetime
from typing import Optional
import logging
import vk_api
from vk_api.exceptions import VkApiError
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class VKParser(BaseParser):
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self.vk: Optional[vk_api.VkApi] = None
    def get_platform_name(self) -> str:
        return "vk"
    def _init_client(self) -> None:
        if self.vk is None:
            self.vk = vk_api.VkApi(token=settings.vk_access_token)
            logger.debug("VK API client initialized")
    async def is_available(self) -> bool:
        try:
            self._init_client()
            api = self.vk.get_api()
            api.groups.getById(group_id=self.account_id)
            return True
        except Exception as e:
            logger.error(f"VK availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        self._init_client()
        async def _fetch() -> PlatformMetrics:
            api = self.vk.get_api()
            group_info = api.groups.getById(
                group_id=self.account_id,
                fields='members_count,description'
            )[0]
            followers = group_info.get('members_count', 0)
            group_id = -group_info['id']
            wall_response = api.wall.get(
                owner_id=group_id,
                count=100,
                offset=0
            )
            posts = wall_response['items']
            posts_count = wall_response['count']
            total_likes = 0
            total_comments = 0
            total_shares = 0
            for post in posts:
                likes = post.get('likes', {}).get('count', 0)
                comments = post.get('comments', {}).get('count', 0)
                reposts = post.get('reposts', {}).get('count', 0)
                total_likes += likes
                total_comments += comments
                total_shares += reposts
            total_engagement = total_likes + total_comments + total_shares
            sample_posts = len(posts)
            engagement_rate = (
                (total_engagement / (followers * sample_posts) * 100)
                if followers > 0 and sample_posts > 0 else 0.0
            )
            return PlatformMetrics(
                platform=self.get_platform_name(),
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=followers,
                posts_count=posts_count,
                total_likes=total_likes,
                total_comments=total_comments,
                total_shares=total_shares,
                engagement_rate=round(engagement_rate, 2),
                extra_data={
                    "group_name": group_info.get('name'),
                    "group_screen_name": group_info.get('screen_name'),
                    "sample_posts": sample_posts,
                    "avg_likes_per_post": round(total_likes / sample_posts, 2) if sample_posts > 0 else 0,
                    "avg_comments_per_post": round(total_comments / sample_posts, 2) if sample_posts > 0 else 0,
                    "avg_shares_per_post": round(total_shares / sample_posts, 2) if sample_posts > 0 else 0
                }
            )
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay,
            exceptions=(VkApiError, ConnectionError, TimeoutError)
        )

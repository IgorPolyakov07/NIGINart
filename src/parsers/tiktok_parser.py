from datetime import datetime, timedelta, date
from typing import Optional, Dict, List
from uuid import UUID
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.models.account import Account
from src.services.token_manager import TokenManager
from src.services.tiktok.marketing_client import TikTokMarketingClient
from src.db.repository import BaseRepository
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class TikTokParser(BaseParser):
    PLATFORM_NAME = "tiktok"
    BASE_URL = "https://open.tiktokapis.com/v2"
    VIDEO_SAMPLE_SIZE = 30
    requires_oauth = True
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self._db: Optional[AsyncSession] = None
        self._db_account_id: Optional[UUID] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._marketing_client: Optional[TikTokMarketingClient] = None
    def set_db_context(self, db: AsyncSession, account_id: UUID) -> None:
        self._db = db
        self._db_account_id = account_id
        logger.debug(f"DB context set for account {account_id}")
    def get_platform_name(self) -> str:
        return self.PLATFORM_NAME
    async def is_available(self) -> bool:
        try:
            if not self._db or not self._db_account_id:
                logger.warning("DB context not set, cannot check availability")
                return False
            client = await self._get_client()
            response = await client.get(
                "/user/info/",
                params={"fields": "open_id,display_name"}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"TikTok API availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        if not self._db or not self._db_account_id:
            raise RuntimeError(
                "Database context not set. Call set_db_context() before fetch_metrics()."
            )
        async def _fetch() -> PlatformMetrics:
            client = await self._get_client()
            user_info = await self._fetch_user_info(client)
            videos = await self._fetch_videos(client)
            aggregated = self._calculate_aggregated_metrics(videos)
            ads_data = await self.fetch_ads_metrics()
            extra_data = {
                "display_name": user_info.get("display_name"),
                "bio_description": user_info.get("bio_description", "")[:200],
                "avatar_url": user_info.get("avatar_url"),
                "is_verified": user_info.get("is_verified", False),
                "profile_deep_link": user_info.get("profile_deep_link"),
                "sample_videos": len(videos),
                "avg_views_per_video": round(aggregated["avg_views"], 2),
                "avg_likes_per_video": round(aggregated["avg_likes"], 2),
                "avg_comments_per_video": round(aggregated["avg_comments"], 2),
                "avg_shares_per_video": round(aggregated["avg_shares"], 2),
                "avg_engagement_rate": round(aggregated["avg_engagement"], 2),
                "recent_videos": videos
            }
            if ads_data:
                extra_data.update(ads_data)
            return PlatformMetrics(
                platform=self.PLATFORM_NAME,
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=user_info.get("follower_count", 0),
                posts_count=user_info.get("video_count", 0),
                total_likes=aggregated["total_likes"],
                total_comments=aggregated["total_comments"],
                total_views=aggregated["total_views"],
                total_shares=aggregated["total_shares"],
                engagement_rate=round(aggregated["avg_engagement"], 2),
                extra_data=extra_data
            )
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay,
            exceptions=(httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
        )
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._marketing_client:
            await self._marketing_client.close()
            self._marketing_client = None
        logger.debug("TikTok HTTP clients closed")
    async def fetch_ads_metrics(self) -> Optional[Dict]:
        marketing_client = await self._get_marketing_client()
        if not marketing_client:
            return None
        account = await self._get_account()
        advertiser_id = account.advertiser_id
        try:
            campaigns = await marketing_client.get_campaigns(advertiser_id)
            periods = {
                "7d": timedelta(days=7),
                "30d": timedelta(days=30),
                "90d": timedelta(days=90),
                "lifetime": None
            }
            ads_metrics = {}
            for period_name, delta in periods.items():
                end_date = date.today()
                start_date = end_date - delta if delta else date(2020, 1, 1)
                report = await marketing_client.get_ad_report(
                    advertiser_id,
                    start_date,
                    end_date
                )
                ads_metrics[period_name] = {
                    "period": period_name,
                    "total_spend": report["total_spend"],
                    "total_impressions": report["total_impressions"],
                    "total_clicks": report["total_clicks"],
                    "total_conversions": report["total_conversions"],
                    "avg_ctr": report["avg_ctr"],
                    "avg_cpm": report["avg_cpm"],
                    "avg_conversion_rate": report["avg_conversion_rate"],
                    "campaigns_count": len(campaigns),
                    "top_campaigns": [
                        {
                            "campaign_id": c.campaign_id,
                            "campaign_name": c.campaign_name,
                            "objective_type": c.objective_type,
                            "budget": c.budget,
                            "status": c.status
                        }
                        for c in sorted(campaigns, key=lambda x: x.budget or 0, reverse=True)[:5]
                    ]
                }
            audience = await marketing_client.get_audience_report(advertiser_id)
            return {
                "ads_metrics": ads_metrics,
                "audience_insights": {
                    "age_distribution": audience.age_distribution,
                    "gender_distribution": audience.gender_distribution,
                    "top_countries": audience.top_countries[:10],
                    "top_interests": audience.top_interests[:20]
                }
            }
        except Exception as e:
            logger.warning(f"Failed to fetch ads metrics: {e}")
            return None
    async def _get_account(self) -> Account:
        account_repo = BaseRepository(Account, self._db)
        account = await account_repo.get(self._db_account_id)
        if not account:
            raise ValueError(f"Account {self._db_account_id} not found in database")
        return account
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            account = await self._get_account()
            token_manager = TokenManager(self._db)
            access_token = await token_manager.get_valid_token(account)
            if not access_token:
                raise RuntimeError(
                    f"No valid OAuth token for account {account.display_name}. "
                    "Please re-authorize via OAuth flow in dashboard."
                )
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            logger.debug(f"TikTok HTTP client initialized for account {account.display_name}")
        return self._client
    async def _get_marketing_client(self) -> Optional[TikTokMarketingClient]:
        if self._marketing_client is None:
            account = await self._get_account()
            if not account.advertiser_id:
                logger.info(f"No advertiser_id for {account.display_name}, skipping ads metrics")
                return None
            token_manager = TokenManager(self._db)
            access_token = await token_manager.get_valid_token(account)
            if not access_token:
                logger.warning("No valid token for Marketing API")
                return None
            self._marketing_client = TikTokMarketingClient(access_token)
            logger.debug(f"Marketing API client initialized for advertiser {account.advertiser_id}")
        return self._marketing_client
    async def _fetch_user_info(self, client: httpx.AsyncClient) -> Dict:
        fields = [
            "open_id",
            "union_id",
            "avatar_url",
            "display_name",
            "bio_description",
            "profile_deep_link",
            "is_verified",
            "follower_count",
            "following_count",
            "likes_count",
            "video_count"
        ]
        response = await client.get(
            "/user/info/",
            params={"fields": ",".join(fields)}
        )
        response.raise_for_status()
        data = response.json()
        if "data" not in data or "user" not in data["data"]:
            logger.error(f"Invalid TikTok user info response: {data}")
            raise ValueError("Invalid TikTok user info response format")
        user_data = data["data"]["user"]
        logger.info(f"Fetched user info for {user_data.get('display_name')}")
        return user_data
    async def _fetch_videos(self, client: httpx.AsyncClient) -> List[Dict]:
        fields = [
            "id",
            "title",
            "create_time",
            "video_description",
            "duration",
            "cover_image_url",
            "share_url",
            "view_count",
            "like_count",
            "comment_count",
            "share_count"
        ]
        response = await client.post(
            "/video/list/",
            json={
                "max_count": self.VIDEO_SAMPLE_SIZE,
                "fields": ",".join(fields)
            }
        )
        response.raise_for_status()
        data = response.json()
        if "data" not in data or "videos" not in data["data"]:
            logger.warning("No videos found in TikTok API response")
            return []
        videos = data["data"]["videos"]
        result = []
        for video in videos:
            views = video.get("view_count", 0)
            likes = video.get("like_count", 0)
            comments = video.get("comment_count", 0)
            shares = video.get("share_count", 0)
            engagement_rate = (
                ((likes + comments + shares) / views * 100) if views > 0 else 0.0
            )
            create_time = video.get("create_time")
            published_at = None
            if create_time:
                published_at = datetime.fromtimestamp(create_time).isoformat() + "+00:00"
            result.append({
                "video_id": video.get("id"),
                "title": video.get("title", "Untitled"),
                "published_at": published_at,
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "duration": video.get("duration", 0),
                "engagement_rate": round(engagement_rate, 2)
            })
        logger.info(f"Fetched {len(result)} videos")
        return result
    def _calculate_aggregated_metrics(self, videos: List[Dict]) -> Dict:
        if not videos:
            return {
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_views": 0.0,
                "avg_likes": 0.0,
                "avg_comments": 0.0,
                "avg_shares": 0.0,
                "avg_engagement": 0.0
            }
        total_views = sum(v["views"] for v in videos)
        total_likes = sum(v["likes"] for v in videos)
        total_comments = sum(v["comments"] for v in videos)
        total_shares = sum(v["shares"] for v in videos)
        count = len(videos)
        avg_engagement = sum(v["engagement_rate"] for v in videos) / count
        return {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_views": total_views / count,
            "avg_likes": total_likes / count,
            "avg_comments": total_comments / count,
            "avg_shares": total_shares / count,
            "avg_engagement": avg_engagement
        }

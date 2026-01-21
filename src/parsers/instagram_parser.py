from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.models.account import Account
from src.services.token_manager import TokenManager
from src.db.repository import BaseRepository
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class InstagramParser(BaseParser):
    PLATFORM_NAME = "instagram"
    MEDIA_SAMPLE_SIZE = 25
    requires_oauth = True
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self._db: Optional[AsyncSession] = None
        self._db_account_id: Optional[UUID] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
    def set_db_context(self, db: AsyncSession, account_id: UUID) -> None:
        self._db = db
        self._db_account_id = account_id
        logger.debug(f"DB context set for Instagram account {account_id}")
    def get_platform_name(self) -> str:
        return self.PLATFORM_NAME
    async def is_available(self) -> bool:
        try:
            if not settings.instagram_system_user_token:
                if not self._db or not self._db_account_id:
                    logger.warning("DB context not set and no System User Token, cannot check availability")
                    return False
            await self._ensure_client()
            is_basic_api = self._access_token and self._access_token.startswith("IG")
            endpoint = "/me" if is_basic_api else f"/{self.account_id}"
            response = await self._client.get(
                endpoint,
                params={
                    "fields": "id,username",
                    "access_token": self._access_token
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Instagram API availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        if not self._db or not self._db_account_id:
            raise RuntimeError(
                "Database context not set. Call set_db_context() before fetch_metrics()."
            )
        async def _fetch() -> PlatformMetrics:
            await self._ensure_client()
            is_basic_api = self._access_token and self._access_token.startswith("IG")
            user_info = await self._fetch_user_info()
            media_list = await self._fetch_media_list()
            if is_basic_api:
                media_insights = media_list
            else:
                media_insights = await self._fetch_media_insights(media_list)
            aggregated = self._calculate_aggregated_metrics(media_insights)
            extra_data = {
                "username": user_info.get("username"),
                "name": user_info.get("name"),
                "profile_picture_url": user_info.get("profile_picture_url"),
                "biography": user_info.get("biography", "")[:300],
                "website": user_info.get("website"),
                "follows_count": user_info.get("follows_count", 0),
                "sample_media": len(media_insights),
                "avg_likes_per_post": round(aggregated["avg_likes"], 2),
                "avg_comments_per_post": round(aggregated["avg_comments"], 2),
                "avg_engagement_rate": round(aggregated["avg_engagement"], 2),
                "avg_reach": round(aggregated["avg_reach"], 2),
                "avg_impressions": round(aggregated["avg_impressions"], 2),
                "avg_saved": round(aggregated["avg_saved"], 2),
                "recent_media": media_insights
            }
            return PlatformMetrics(
                platform=self.PLATFORM_NAME,
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=user_info.get("followers_count", 0),
                posts_count=user_info.get("media_count", 0),
                total_likes=aggregated["total_likes"],
                total_comments=aggregated["total_comments"],
                total_views=aggregated["total_impressions"],
                total_shares=aggregated["total_saved"],
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
        logger.debug("Instagram HTTP client closed")
    async def _get_account(self) -> Account:
        account_repo = BaseRepository(Account, self._db)
        account = await account_repo.get(self._db_account_id)
        if not account:
            raise ValueError(f"Account {self._db_account_id} not found in database")
        return account
    async def _get_access_token(self) -> str:
        if settings.instagram_system_user_token:
            logger.info("Using System User Token for Instagram API")
            return settings.instagram_system_user_token
        account = await self._get_account()
        token_manager = TokenManager(self._db)
        access_token = await token_manager.get_valid_token(account)
        if not access_token:
            raise RuntimeError(
                f"No valid token for Instagram account {account.display_name}. "
                "Please set INSTAGRAM_SYSTEM_USER_TOKEN or re-authorize via OAuth in dashboard."
            )
        logger.info(f"Using User OAuth token for Instagram account {account.display_name}")
        return access_token
    async def _ensure_client(self) -> None:
        if self._client is None:
            self._access_token = await self._get_access_token()
            if self._access_token and self._access_token.startswith("IG"):
                base_url = "https://graph.instagram.com"
                logger.info("Using Instagram Basic Display API (graph.instagram.com)")
            else:
                base_url = f"https://graph.facebook.com/{settings.facebook_graph_api_version}"
                logger.info("Using Instagram Graph API (graph.facebook.com)")
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0
            )
            logger.debug("Instagram HTTP client initialized")
    async def _fetch_user_info(self) -> Dict:
        is_basic_api = self._access_token and self._access_token.startswith("IG")
        if is_basic_api:
            fields = ["id", "username", "account_type", "media_count", "followers_count"]
            endpoint = "/me"
        else:
            fields = [
                "id", "username", "name", "profile_picture_url",
                "biography", "website", "followers_count",
                "follows_count", "media_count"
            ]
            endpoint = f"/{self.account_id}"
        response = await self._client.get(
            endpoint,
            params={
                "fields": ",".join(fields),
                "access_token": self._access_token
            }
        )
        response.raise_for_status()
        data = response.json()
        if "id" not in data:
            logger.error(f"Invalid Instagram user info response: {data}")
            raise ValueError("Invalid Instagram user info response format")
        logger.info(f"Fetched user info for @{data.get('username')}")
        return data
    async def _fetch_media_list(self) -> List[Dict]:
        is_basic_api = self._access_token and self._access_token.startswith("IG")
        if is_basic_api:
            fields = ["id", "caption", "media_type", "media_url", "permalink", "timestamp"]
            endpoint = "/me/media"
        else:
            fields = [
                "id", "caption", "media_type", "media_url",
                "permalink", "timestamp", "like_count", "comments_count"
            ]
            endpoint = f"/{self.account_id}/media"
        response = await self._client.get(
            endpoint,
            params={
                "fields": ",".join(fields),
                "limit": self.MEDIA_SAMPLE_SIZE,
                "access_token": self._access_token
            }
        )
        response.raise_for_status()
        data = response.json()
        if "data" not in data:
            logger.warning("No media found in Instagram API response")
            return []
        media_list = data["data"]
        logger.info(f"Fetched {len(media_list)} media items")
        return media_list
    async def _fetch_media_insights(self, media_list: List[Dict]) -> List[Dict]:
        result = []
        for media in media_list:
            media_id = media.get("id")
            media_type = media.get("media_type")
            if media_type not in ["IMAGE", "VIDEO", "CAROUSEL_ALBUM"]:
                continue
            try:
                insights_response = await self._client.get(
                    f"/{media_id}/insights",
                    params={
                        "metric": "impressions,reach,saved,engagement",
                        "access_token": self._access_token
                    }
                )
                insights_response.raise_for_status()
                insights_data = insights_response.json()
                insights = {}
                for metric in insights_data.get("data", []):
                    metric_name = metric.get("name")
                    metric_value = metric.get("values", [{}])[0].get("value", 0)
                    insights[metric_name] = metric_value
                impressions = insights.get("impressions", 0)
                engagement = insights.get("engagement", 0)
                engagement_rate = (engagement / impressions * 100) if impressions > 0 else 0.0
                result.append({
                    "media_id": media_id,
                    "caption": (media.get("caption") or "")[:100],
                    "media_type": media_type,
                    "permalink": media.get("permalink"),
                    "timestamp": media.get("timestamp"),
                    "likes": media.get("like_count", 0),
                    "comments": media.get("comments_count", 0),
                    "impressions": insights.get("impressions", 0),
                    "reach": insights.get("reach", 0),
                    "saved": insights.get("saved", 0),
                    "engagement": insights.get("engagement", 0),
                    "engagement_rate": round(engagement_rate, 2)
                })
            except httpx.HTTPStatusError as e:
                logger.warning(f"Failed to fetch insights for media {media_id}: {e}")
                continue
        logger.info(f"Fetched insights for {len(result)} media items")
        return result
    def _calculate_aggregated_metrics(self, media_insights: List[Dict]) -> Dict:
        default_result = {
            "total_likes": 0,
            "total_comments": 0,
            "total_impressions": 0,
            "total_reach": 0,
            "total_saved": 0,
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "avg_impressions": 0.0,
            "avg_reach": 0.0,
            "avg_saved": 0.0,
            "avg_engagement": 0.0
        }
        if not media_insights:
            return default_result
        total_likes = sum(m.get("likes", m.get("like_count", 0)) for m in media_insights)
        total_comments = sum(m.get("comments", m.get("comments_count", 0)) for m in media_insights)
        total_impressions = sum(m.get("impressions", 0) for m in media_insights)
        total_reach = sum(m.get("reach", 0) for m in media_insights)
        total_saved = sum(m.get("saved", 0) for m in media_insights)
        count = len(media_insights)
        avg_engagement = sum(m.get("engagement_rate", 0) for m in media_insights) / count if count else 0
        return {
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_impressions": total_impressions,
            "total_reach": total_reach,
            "total_saved": total_saved,
            "avg_likes": total_likes / count,
            "avg_comments": total_comments / count,
            "avg_impressions": total_impressions / count,
            "avg_reach": total_reach / count,
            "avg_saved": total_saved / count,
            "avg_engagement": avg_engagement
        }

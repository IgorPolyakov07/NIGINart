from datetime import datetime, timedelta
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
class PinterestParser(BaseParser):
    PLATFORM_NAME = "pinterest"
    BASE_URL = "https://api.pinterest.com/v5"
    requires_oauth = True
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self._db: Optional[AsyncSession] = None
        self._db_account_id: Optional[UUID] = None
        self._client: Optional[httpx.AsyncClient] = None
    def set_db_context(self, db: AsyncSession, account_id: UUID) -> None:
        self._db = db
        self._db_account_id = account_id
        logger.debug(f"DB context set for Pinterest account {account_id}")
    def get_platform_name(self) -> str:
        return self.PLATFORM_NAME
    async def is_available(self) -> bool:
        try:
            if not self._db or not self._db_account_id:
                logger.warning("DB context not set, cannot check availability")
                return False
            client = await self._get_client()
            response = await client.get("/user_account")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Pinterest API availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        if not self._db or not self._db_account_id:
            raise RuntimeError(
                "Database context not set. Call set_db_context() before fetch_metrics()."
            )
        async def _fetch() -> PlatformMetrics:
            client = await self._get_client()
            user_info = await self._fetch_user_info(client)
            analytics = await self._fetch_analytics(client)
            top_pins = await self._fetch_top_pins(client)
            aggregated = self._calculate_aggregated_metrics(top_pins)
            extra_data = {
                "username": user_info.get("username"),
                "business_name": user_info.get("business_name"),
                "about": user_info.get("about", "")[:200],
                "profile_image": user_info.get("profile_image"),
                "website_url": user_info.get("website_url"),
                "account_type": user_info.get("account_type"),
                "board_count": user_info.get("board_count", 0),
                "following_count": user_info.get("following_count", 0),
                "impressions_30d": analytics.get("IMPRESSION", 0),
                "engagements_30d": analytics.get("ENGAGEMENT", 0),
                "saves_30d": analytics.get("SAVE", 0),
                "pin_clicks_30d": analytics.get("PIN_CLICK", 0),
                "outbound_clicks_30d": analytics.get("OUTBOUND_CLICK", 0),
                "video_starts_30d": analytics.get("VIDEO_START", 0),
                "video_views_30d": analytics.get("VIDEO_MRC_VIEW", 0),
                "engagement_rate_30d": analytics.get("ENGAGEMENT_RATE", 0),
                "save_rate_30d": analytics.get("SAVE_RATE", 0),
                "pin_click_rate_30d": analytics.get("PIN_CLICK_RATE", 0),
                "outbound_click_rate_30d": analytics.get("OUTBOUND_CLICK_RATE", 0),
                "top_pins_count": len(top_pins),
                "top_pins": top_pins[:10],
                "avg_impressions_per_pin": aggregated.get("avg_impressions", 0),
                "avg_saves_per_pin": aggregated.get("avg_saves", 0),
                "avg_clicks_per_pin": aggregated.get("avg_clicks", 0),
            }
            impressions = analytics.get("IMPRESSION", 0)
            engagement = analytics.get("ENGAGEMENT", 0)
            engagement_rate = (engagement / impressions * 100) if impressions > 0 else 0.0
            return PlatformMetrics(
                platform=self.PLATFORM_NAME,
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=user_info.get("follower_count", 0),
                posts_count=user_info.get("pin_count", 0),
                total_views=user_info.get("monthly_views", 0),
                total_likes=analytics.get("SAVE", 0),
                total_comments=0,
                total_shares=analytics.get("OUTBOUND_CLICK", 0),
                engagement_rate=round(engagement_rate, 2),
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
            logger.debug("Pinterest HTTP client closed")
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
                    f"No valid OAuth token for Pinterest account {account.display_name}. "
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
            logger.debug(f"Pinterest HTTP client initialized for account {account.display_name}")
        return self._client
    async def _fetch_user_info(self, client: httpx.AsyncClient) -> Dict:
        response = await client.get("/user_account")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched Pinterest user info for {data.get('username')}")
        return data
    async def _fetch_analytics(self, client: httpx.AsyncClient) -> Dict:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)
        try:
            response = await client.get(
                "/user_account/analytics",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "content_type": "ORGANIC",
                    "metric_types": ",".join([
                        "IMPRESSION",
                        "ENGAGEMENT",
                        "ENGAGEMENT_RATE",
                        "PIN_CLICK",
                        "PIN_CLICK_RATE",
                        "OUTBOUND_CLICK",
                        "OUTBOUND_CLICK_RATE",
                        "SAVE",
                        "SAVE_RATE",
                        "VIDEO_START",
                        "VIDEO_MRC_VIEW",
                    ])
                }
            )
            response.raise_for_status()
            data = response.json()
            if data and isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "summary_metrics" in value:
                        logger.info("Fetched Pinterest analytics for last 30 days")
                        return value["summary_metrics"]
            logger.warning("No analytics data found in Pinterest response")
            return {}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("No permission to access Pinterest analytics")
            else:
                logger.error(f"Pinterest analytics fetch failed: {e}")
            return {}
    async def _fetch_top_pins(self, client: httpx.AsyncClient) -> List[Dict]:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)
        try:
            response = await client.get(
                "/user_account/analytics/top_pins",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "sort_by": "IMPRESSION",
                    "content_type": "ORGANIC",
                    "num_of_pins": 50,
                    "metric_types": ",".join([
                        "IMPRESSION",
                        "SAVE",
                        "PIN_CLICK",
                        "OUTBOUND_CLICK",
                    ])
                }
            )
            response.raise_for_status()
            data = response.json()
            pins = data.get("pins", [])
            result = []
            for pin in pins:
                metrics = pin.get("metrics", {})
                result.append({
                    "pin_id": pin.get("id"),
                    "organic_pin_id": pin.get("organic_pin_id"),
                    "impressions": metrics.get("IMPRESSION", 0),
                    "saves": metrics.get("SAVE", 0),
                    "pin_clicks": metrics.get("PIN_CLICK", 0),
                    "outbound_clicks": metrics.get("OUTBOUND_CLICK", 0),
                })
            logger.info(f"Fetched {len(result)} top Pinterest pins")
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("No permission to access Pinterest top pins analytics")
            else:
                logger.error(f"Pinterest top pins fetch failed: {e}")
            return []
    def _calculate_aggregated_metrics(self, pins: List[Dict]) -> Dict:
        if not pins:
            return {
                "avg_impressions": 0.0,
                "avg_saves": 0.0,
                "avg_clicks": 0.0,
            }
        total_impressions = sum(p.get("impressions", 0) for p in pins)
        total_saves = sum(p.get("saves", 0) for p in pins)
        total_clicks = sum(p.get("pin_clicks", 0) for p in pins)
        count = len(pins)
        return {
            "avg_impressions": round(total_impressions / count, 2),
            "avg_saves": round(total_saves / count, 2),
            "avg_clicks": round(total_clicks / count, 2),
        }

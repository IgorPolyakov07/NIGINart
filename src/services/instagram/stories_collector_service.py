import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import get_settings
from src.db.repository import BaseRepository
from src.models.account import Account
from src.models.instagram_story_snapshot import InstagramStorySnapshot
from src.services.token_manager import TokenManager
logger = logging.getLogger(__name__)
settings = get_settings()
class CollectionResult:
    def __init__(self):
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.status: str = "success"
        self.accounts_processed: int = 0
        self.accounts_failed: int = 0
        self.success_details: List[Dict] = []
        self.error_details: List[Dict] = []
class InstagramStoriesCollectorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = BaseRepository(Account, db)
        self.snapshot_repo = BaseRepository(InstagramStorySnapshot, db)
        self._http_client: Optional[httpx.AsyncClient] = None
    async def collect_all(self) -> CollectionResult:
        result = CollectionResult()
        result.started_at = datetime.utcnow()
        try:
            accounts = await self._get_active_instagram_accounts()
            logger.info(
                f"📸 Found {len(accounts)} active Instagram accounts for story collection"
            )
            for account in accounts:
                try:
                    account_result = await self._collect_account_stories(account)
                    result.accounts_processed += 1
                    result.success_details.append(
                        {
                            "account_id": str(account.id),
                            "account_name": account.display_name,
                            "stories_collected": account_result["stories_collected"],
                            "snapshots_saved": account_result["snapshots_saved"],
                        }
                    )
                except Exception as e:
                    logger.error(
                        f"❌ Failed to collect stories for {account.display_name}: {e}",
                        exc_info=True,
                    )
                    result.accounts_failed += 1
                    result.error_details.append(
                        {
                            "account_id": str(account.id),
                            "account_name": account.display_name,
                            "error": str(e),
                        }
                    )
            result.finished_at = datetime.utcnow()
            result.status = (
                "success"
                if result.accounts_failed == 0
                else "partial" if result.accounts_processed > 0 else "failed"
            )
            logger.info(
                f"✅ Stories collection completed. "
                f"Status: {result.status}, "
                f"Processed: {result.accounts_processed}, "
                f"Failed: {result.accounts_failed}"
            )
        except Exception as e:
            result.finished_at = datetime.utcnow()
            result.status = "failed"
            logger.error(f"❌ Stories collection run failed: {e}", exc_info=True)
            raise
        return result
    async def collect_account_stories(self, account_id: UUID) -> Dict:
        account = await self.account_repo.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        if account.platform != "instagram":
            raise ValueError(
                f"Account {account_id} is not Instagram (platform={account.platform})"
            )
        return await self._collect_account_stories(account)
    async def _get_active_instagram_accounts(self) -> List[Account]:
        query = select(Account).where(
            Account.platform == "instagram", Account.is_active == True
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    async def _collect_account_stories(self, account: Account) -> Dict:
        logger.info(f"📸 Collecting stories for {account.display_name}")
        access_token = await self._get_access_token(account)
        stories = await self._fetch_active_stories(account.account_id, access_token)
        if not stories:
            logger.info(f"ℹ️ No active stories found for {account.display_name}")
            return {"stories_collected": 0, "snapshots_saved": 0}
        logger.info(
            f"📊 Found {len(stories)} active stories for {account.display_name}"
        )
        snapshots_saved = 0
        for story in stories:
            try:
                if await self._is_recently_collected(story["id"]):
                    logger.debug(
                        f"⏭️ Skipping story {story['id']} (already collected recently)"
                    )
                    continue
                insights = await self._fetch_story_insights(story["id"], access_token)
                await self._save_snapshot(account.id, story, insights)
                snapshots_saved += 1
            except Exception as e:
                logger.error(
                    f"❌ Failed to process story {story.get('id')}: {e}",
                    exc_info=True,
                )
                continue
        logger.info(
            f"✅ Saved {snapshots_saved} story snapshots for {account.display_name}"
        )
        return {"stories_collected": len(stories), "snapshots_saved": snapshots_saved}
    async def _get_access_token(self, account: Account) -> str:
        if settings.instagram_system_user_token:
            return settings.instagram_system_user_token
        token_manager = TokenManager(self.db)
        access_token = await token_manager.get_valid_token(account)
        if not access_token:
            raise RuntimeError(
                f"No valid token for {account.display_name}. "
                "Please re-authorize via dashboard."
            )
        return access_token
    async def _fetch_active_stories(
        self, instagram_account_id: str, access_token: str
    ) -> List[Dict]:
        client = await self._get_http_client()
        response = await client.get(
            f"https://graph.facebook.com/{settings.facebook_graph_api_version}/{instagram_account_id}/stories",
            params={
                "fields": "id,media_type,media_url,timestamp",
                "access_token": access_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        stories = data.get("data", [])
        now = datetime.utcnow()
        active_stories = []
        for story in stories:
            timestamp_str = story.get("timestamp")
            if timestamp_str:
                posted_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                posted_at = posted_at.replace(tzinfo=None)
                expires_at = posted_at + timedelta(hours=24)
                if expires_at > now:
                    active_stories.append(
                        {
                            **story,
                            "posted_at": posted_at,
                            "expires_at": expires_at,
                        }
                    )
        return active_stories
    async def _fetch_story_insights(
        self, story_id: str, access_token: str
    ) -> Dict:
        client = await self._get_http_client()
        metrics = "reach,impressions,exits,replies,taps_forward,taps_back"
        response = await client.get(
            f"https://graph.facebook.com/{settings.facebook_graph_api_version}/{story_id}/insights",
            params={"metric": metrics, "access_token": access_token},
        )
        response.raise_for_status()
        data = response.json()
        insights = {}
        for metric in data.get("data", []):
            metric_name = metric.get("name")
            metric_values = metric.get("values", [{}])
            metric_value = metric_values[0].get("value", 0) if metric_values else 0
            insights[metric_name] = metric_value
        return insights
    async def _is_recently_collected(
        self, story_id: str, threshold_hours: int = 1
    ) -> bool:
        threshold_time = datetime.utcnow() - timedelta(hours=threshold_hours)
        query = select(InstagramStorySnapshot).where(
            InstagramStorySnapshot.story_id == story_id,
            InstagramStorySnapshot.collected_at >= threshold_time,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    async def _save_snapshot(
        self, account_id: UUID, story: Dict, insights: Dict
    ) -> None:
        impressions = insights.get("impressions", 0)
        exits = insights.get("exits", 0)
        completion_rate = (
            ((impressions - exits) / impressions * 100) if impressions > 0 else 0.0
        )
        extra_data = {
            "raw_insights": insights,
            "story_metadata": {
                "timestamp_iso": story.get("timestamp"),
                "media_url": story.get("media_url"),
            },
        }
        await self.snapshot_repo.create(
            account_id=account_id,
            story_id=story["id"],
            collected_at=datetime.utcnow(),
            posted_at=story["posted_at"],
            retention_expires_at=story["expires_at"],
            media_type=story.get("media_type", "IMAGE"),
            media_url=story.get("media_url"),
            reach=insights.get("reach"),
            impressions=impressions,
            exits=exits,
            replies=insights.get("replies"),
            taps_forward=insights.get("taps_forward"),
            taps_back=insights.get("taps_back"),
            completion_rate=round(completion_rate, 2),
            extra_data=extra_data,
        )
        await self.db.commit()
        logger.debug(f"💾 Saved snapshot for story {story['id']}")
    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=settings.api_timeout_seconds
            )
        return self._http_client
    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

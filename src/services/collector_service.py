from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.account import Account
from src.models.metric import Metric
from src.models.collection_log import CollectionLog
from src.parsers.factory import ParserFactory
from src.parsers.base import PlatformMetrics
from src.db.repository import BaseRepository
logger = logging.getLogger(__name__)
class CollectionResult:
    def __init__(self):
        self.log_id: Optional[UUID] = None
        self.started_at: datetime = datetime.utcnow()
        self.finished_at: Optional[datetime] = None
        self.accounts_processed: int = 0
        self.accounts_failed: int = 0
        self.success_details: List[Dict] = []
        self.error_details: List[Dict] = []
    @property
    def status(self) -> str:
        if self.accounts_failed == 0:
            return "success"
        elif self.accounts_processed > 0:
            return "partial"
        return "failed"
class CollectorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = BaseRepository(Account, db)
        self.metric_repo = BaseRepository(Metric, db)
        self.log_repo = BaseRepository(CollectionLog, db)
    async def collect_all(
        self,
        platform_filter: Optional[str] = None
    ) -> CollectionResult:
        result = CollectionResult()
        log = await self.log_repo.create(
            started_at=result.started_at,
            status="running",
            accounts_processed=0,
            accounts_failed=0
        )
        result.log_id = log.id
        await self.db.commit()
        logger.info(f"Collection started. Log ID: {log.id}")
        try:
            accounts = await self._get_active_accounts(platform_filter)
            logger.info(f"Found {len(accounts)} active accounts to process")
            if platform_filter:
                logger.info(f"Platform filter: {platform_filter}")
            for account in accounts:
                try:
                    await self._collect_account(account, result)
                except Exception as e:
                    logger.error(
                        f"Failed to collect {account.platform}:{account.account_id}: {e}",
                        exc_info=True
                    )
                    result.accounts_failed += 1
                    result.error_details.append({
                        "account_id": str(account.id),
                        "platform": account.platform,
                        "account_name": account.account_id,
                        "error": str(e)
                    })
            result.finished_at = datetime.utcnow()
            await self.log_repo.update(
                log.id,
                finished_at=result.finished_at,
                status=result.status,
                accounts_processed=result.accounts_processed,
                accounts_failed=result.accounts_failed,
                error_message=self._format_errors(result.error_details) if result.error_details else None
            )
            await self.db.commit()
            logger.info(
                f"Collection completed. Status: {result.status}, "
                f"Success: {result.accounts_processed}, Failed: {result.accounts_failed}"
            )
        except Exception as e:
            result.finished_at = datetime.utcnow()
            logger.error(f"Collection run failed: {e}", exc_info=True)
            await self.log_repo.update(
                log.id,
                finished_at=result.finished_at,
                status="failed",
                error_message=str(e)
            )
            await self.db.commit()
            raise
        return result
    async def _get_active_accounts(self, platform_filter: Optional[str] = None) -> List[Account]:
        query = select(Account).where(Account.is_active == True)
        if platform_filter:
            query = query.where(Account.platform == platform_filter.lower())
        result = await self.db.execute(query)
        accounts = list(result.scalars().all())
        logger.debug(f"Fetched {len(accounts)} active accounts")
        return accounts
    async def _collect_account(self, account: Account, result: CollectionResult) -> None:
        logger.info(f"Collecting metrics for {account.platform}:{account.account_id}")
        parser = ParserFactory.create(
            account.platform,
            account.account_id,
            account.account_url
        )
        if hasattr(parser, 'set_db_context'):
            parser.set_db_context(self.db, account.id)
        try:
            is_available = await parser.is_available()
            if not is_available:
                raise RuntimeError(f"Platform {account.platform} is not available")
            metrics = await parser.fetch_metrics()
            await self._save_metrics(account.id, metrics)
            result.accounts_processed += 1
            result.success_details.append({
                "account_id": str(account.id),
                "platform": account.platform,
                "account_name": account.account_id,
                "metrics": {
                    "followers": metrics.followers,
                    "engagement_rate": metrics.engagement_rate
                }
            })
            logger.info(
                f"Successfully collected {account.platform}:{account.account_id} - "
                f"Followers: {metrics.followers}, ER: {metrics.engagement_rate}%"
            )
        finally:
            if hasattr(parser, 'close'):
                await parser.close()
    async def _save_metrics(self, account_id: UUID, metrics: PlatformMetrics) -> None:
        await self.metric_repo.create(
            account_id=account_id,
            collected_at=metrics.collected_at,
            followers=metrics.followers,
            posts_count=metrics.posts_count,
            total_likes=metrics.total_likes,
            total_comments=metrics.total_comments,
            total_views=metrics.total_views,
            total_shares=metrics.total_shares,
            engagement_rate=metrics.engagement_rate,
            extra_data=metrics.extra_data
        )
        await self.db.commit()
        logger.debug(f"Saved metrics for account {account_id}")
    @staticmethod
    def _format_errors(errors: List[Dict]) -> str:
        return "; ".join(
            f"{e['platform']}:{e['account_name']} - {e.get('error', 'Unknown error')}"
            for e in errors
        )

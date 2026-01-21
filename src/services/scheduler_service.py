import logging
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from src.db.database import async_session_factory
from src.services.collector_service import CollectorService
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class SchedulerService:
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._running = False
    async def start(self) -> None:
        if self._running:
            logger.warning("Scheduler already running")
            return
        try:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.add_listener(
                self._job_executed_listener,
                EVENT_JOB_EXECUTED
            )
            self.scheduler.add_listener(
                self._job_error_listener,
                EVENT_JOB_ERROR
            )
            self.scheduler.add_job(
                self._collection_job,
                trigger=IntervalTrigger(hours=settings.collect_interval_hours),
                id='auto_collection',
                name='Automatic metric collection',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            if settings.instagram_stories_collection_enabled:
                self.scheduler.add_job(
                    self._instagram_stories_collection_job,
                    trigger=IntervalTrigger(hours=1),
                    id='instagram_stories_collection',
                    name='Instagram Stories hourly collection',
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True
                )
                logger.info("Instagram Stories hourly collection enabled")
            self.scheduler.start()
            self._running = True
            stories_status = "enabled (1h)" if settings.instagram_stories_collection_enabled else "disabled"
            logger.info(
                f"✅ Scheduler started. Main collection: {settings.collect_interval_hours}h, "
                f"Stories collection: {stories_status}"
            )
            await self._collection_job()
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}", exc_info=True)
    async def stop(self) -> None:
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")
    async def _collection_job(self) -> None:
        logger.info("🔄 Starting scheduled collection...")
        async with async_session_factory() as db:
            try:
                service = CollectorService(db)
                result = await service.collect_all()
                logger.info(
                    f"✅ Scheduled collection completed. "
                    f"Status: {result.status}, "
                    f"Processed: {result.accounts_processed}, "
                    f"Failed: {result.accounts_failed}"
                )
            except Exception as e:
                logger.error(f"❌ Scheduled collection failed: {e}", exc_info=True)
    async def _instagram_stories_collection_job(self) -> None:
        logger.info("📸 Starting Instagram Stories hourly collection...")
        async with async_session_factory() as db:
            service = None
            try:
                from src.services.instagram.stories_collector_service import (
                    InstagramStoriesCollectorService,
                )
                service = InstagramStoriesCollectorService(db)
                result = await service.collect_all()
                logger.info(
                    f"✅ Instagram Stories collection completed. "
                    f"Processed: {result.accounts_processed}, "
                    f"Failed: {result.accounts_failed}"
                )
                total_snapshots = sum(
                    d.get("snapshots_saved", 0) for d in result.success_details
                )
                logger.info(f"📊 Total story snapshots saved: {total_snapshots}")
            except Exception as e:
                logger.error(
                    f"❌ Instagram Stories collection failed: {e}", exc_info=True
                )
            finally:
                if service:
                    await service.close()
    @staticmethod
    def _job_executed_listener(event) -> None:
        logger.info(f"Job '{event.job_id}' executed successfully")
    @staticmethod
    def _job_error_listener(event) -> None:
        logger.error(f"Job '{event.job_id}' failed: {event.exception}")

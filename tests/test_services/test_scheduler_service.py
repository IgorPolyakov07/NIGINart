import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.services.scheduler_service import SchedulerService
class TestSchedulerService:
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        scheduler = SchedulerService()
        with patch('src.services.scheduler_service.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler_instance = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler_instance
            with patch.object(scheduler, '_collection_job', new_callable=AsyncMock):
                await scheduler.start()
                assert scheduler._running is True
                mock_scheduler_instance.start.assert_called_once()
                await scheduler.stop()
                assert scheduler._running is False
                mock_scheduler_instance.shutdown.assert_called_once_with(wait=True)
    @pytest.mark.asyncio
    async def test_collection_job_execution(self):
        scheduler = SchedulerService()
        mock_result = MagicMock()
        mock_result.status = 'success'
        mock_result.accounts_processed = 3
        mock_result.accounts_failed = 0
        with patch('src.services.scheduler_service.async_session_factory') as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_factory.return_value = mock_session
            with patch('src.services.scheduler_service.CollectorService') as mock_collector:
                mock_collector_instance = MagicMock()
                mock_collector_instance.collect_all = AsyncMock(return_value=mock_result)
                mock_collector.return_value = mock_collector_instance
                await scheduler._collection_job()
                mock_collector_instance.collect_all.assert_called_once()
    @pytest.mark.asyncio
    async def test_scheduler_non_blocking_failure(self):
        scheduler = SchedulerService()
        with patch('src.services.scheduler_service.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler_class.side_effect = Exception("Scheduler initialization failed")
            with patch.object(scheduler, '_collection_job', new_callable=AsyncMock):
                await scheduler.start()
                assert scheduler._running is False
    @pytest.mark.asyncio
    async def test_interval_configuration(self):
        scheduler = SchedulerService()
        with patch('src.services.scheduler_service.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler_instance = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler_instance
            with patch('src.services.scheduler_service.settings') as mock_settings:
                mock_settings.collect_interval_hours = 12
                with patch.object(scheduler, '_collection_job', new_callable=AsyncMock):
                    await scheduler.start()
                    call_kwargs = mock_scheduler_instance.add_job.call_args[1]
                    trigger = call_kwargs['trigger']
                    assert trigger.interval.total_seconds() == 12 * 3600
    @pytest.mark.asyncio
    async def test_scheduler_already_running_warning(self):
        scheduler = SchedulerService()
        scheduler._running = True
        with patch('src.services.scheduler_service.logger') as mock_logger:
            await scheduler.start()
            mock_logger.warning.assert_called_with("Scheduler already running")
    @pytest.mark.asyncio
    async def test_collection_job_handles_errors(self):
        scheduler = SchedulerService()
        with patch('src.services.scheduler_service.async_session_factory') as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_factory.return_value = mock_session
            with patch('src.services.scheduler_service.CollectorService') as mock_collector:
                mock_collector.side_effect = Exception("Collection failed")
                await scheduler._collection_job()

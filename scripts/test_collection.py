import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.config.settings import get_settings
from src.services.collector_service import CollectorService
from src.models.account import Account
from src.models.metric import Metric
from src.models.collection_log import CollectionLog
settings = get_settings()
class CollectionTester:
    def __init__(self):
        self.engine = create_async_engine(str(settings.database_url))
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    @staticmethod
    def print_header(text: str) -> None:
        print(f"\n{'=' * 70}")
        print(f"  {text}")
        print(f"{'=' * 70}\n")
    @staticmethod
    def print_success(text: str) -> None:
        print(f"✅ {text}")
    @staticmethod
    def print_error(text: str) -> None:
        print(f"❌ {text}")
    @staticmethod
    def print_info(text: str) -> None:
        print(f"ℹ️  {text}")
    async def check_database_connection(self) -> bool:
        self.print_info("Checking database connection...")
        try:
            async with self.session_maker() as session:
                result = await session.execute(select(func.count()).select_from(Account))
                count = result.scalar()
                self.print_success(f"Database connected! Found {count} accounts")
                return True
        except Exception as e:
            self.print_error(f"Database connection failed: {e}")
            return False
    async def get_active_accounts(self, platforms: List[str] = None) -> List[Account]:
        async with self.session_maker() as session:
            query = select(Account).where(Account.is_active == True)
            if platforms:
                query = query.where(Account.platform.in_(platforms))
            result = await session.execute(query)
            return list(result.scalars().all())
    async def run_collection(self, platform_filter: str = None) -> None:
        self.print_header(f"Running Collection Service")
        if platform_filter:
            self.print_info(f"Platform filter: {platform_filter}")
        else:
            self.print_info("Collecting from all platforms")
        async with self.session_maker() as session:
            service = CollectorService(session)
            self.print_info("Starting collection...")
            start_time = datetime.now()
            result = await service.collect_all(platform_filter=platform_filter)
            duration = (datetime.now() - start_time).total_seconds()
            self.print_header("Collection Results")
            print(f"Status:              {result.status}")
            print(f"Accounts Processed:  {result.accounts_processed}")
            print(f"Accounts Failed:     {result.accounts_failed}")
            print(f"Duration:            {duration:.2f}s")
            print(f"Started At:          {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Finished At:         {result.finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if result.success_details:
                self.print_header("Successful Collections")
                for detail in result.success_details:
                    platform = detail['platform']
                    account = detail['account_id']
                    print(f"✅ {platform.upper()}: {account}")
            if result.error_details:
                self.print_header("Failed Collections")
                for detail in result.error_details:
                    platform = detail['platform']
                    account = detail['account_id']
                    error = detail['error']
                    print(f"❌ {platform.upper()}: {account}")
                    print(f"   Error: {error}")
    async def verify_database_data(self) -> None:
        self.print_header("Database Verification")
        async with self.session_maker() as session:
            accounts_count = await session.scalar(select(func.count()).select_from(Account))
            metrics_count = await session.scalar(select(func.count()).select_from(Metric))
            logs_count = await session.scalar(select(func.count()).select_from(CollectionLog))
            print(f"Total Accounts:        {accounts_count}")
            print(f"Total Metrics:         {metrics_count}")
            print(f"Total Collection Logs: {logs_count}")
            result = await session.execute(
                select(Metric.platform, func.count(Metric.id))
                .group_by(Metric.platform)
            )
            platform_metrics = result.all()
            if platform_metrics:
                self.print_header("Metrics by Platform")
                for platform, count in platform_metrics:
                    print(f"{platform.upper()}: {count} metrics")
            result = await session.execute(
                select(Metric)
                .order_by(Metric.collected_at.desc())
                .limit(5)
            )
            recent_metrics = result.scalars().all()
            if recent_metrics:
                self.print_header("Recent Metrics (Last 5)")
                for metric in recent_metrics:
                    print(f"\n{metric.platform.upper()} - {metric.account_id}")
                    print(f"   Followers:     {metric.followers:,}")
                    print(f"   Engagement:    {metric.engagement_rate:.2f}%")
                    print(f"   Collected:     {metric.collected_at.strftime('%Y-%m-%d %H:%M:%S')}")
    async def run_full_test(self, platforms: List[str] = None) -> None:
        self.print_header("Collection Service Full Test Suite")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if not await self.check_database_connection():
            self.print_error("Cannot proceed without database connection")
            return
        platforms_str = ', '.join(platforms) if platforms else 'all'
        self.print_info(f"Testing platforms: {platforms_str}")
        accounts = await self.get_active_accounts(platforms)
        if not accounts:
            self.print_error(f"No active accounts found for platforms: {platforms_str}")
            return
        self.print_success(f"Found {len(accounts)} active accounts")
        for account in accounts:
            print(f"   - {account.platform.upper()}: {account.account_id}")
        for platform in (platforms or ['telegram', 'youtube']):
            await self.run_collection(platform_filter=platform)
            print()
        await self.verify_database_data()
        self.print_header("Test Complete")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    async def cleanup(self) -> None:
        await self.engine.dispose()
async def main():
    platforms = ['telegram', 'youtube']
    tester = CollectionTester()
    try:
        await tester.run_full_test(platforms=platforms)
    finally:
        await tester.cleanup()
if __name__ == "__main__":
    asyncio.run(main())

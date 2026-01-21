import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.parsers.factory import ParserFactory
from src.parsers.base import PlatformMetrics
from src.config.settings import get_settings
settings = get_settings()
class ParserTester:
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
    @staticmethod
    def print_header(text: str) -> None:
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print(f"{'=' * 60}\n")
    @staticmethod
    def print_success(text: str) -> None:
        print(f"✅ {text}")
    @staticmethod
    def print_error(text: str) -> None:
        print(f"❌ {text}")
    @staticmethod
    def print_info(text: str) -> None:
        print(f"ℹ️  {text}")
    def print_metrics(self, metrics: PlatformMetrics) -> None:
        print(f"\n📊 Результаты сбора:")
        print(f"   Platform:         {metrics.platform}")
        print(f"   Account ID:       {metrics.account_id}")
        print(f"   Followers:        {metrics.followers:,}")
        print(f"   Posts:            {metrics.posts_count:,}")
        print(f"   Total Views:      {metrics.total_views:,}")
        print(f"   Total Likes:      {metrics.total_likes or 'N/A'}")
        print(f"   Total Comments:   {metrics.total_comments or 'N/A'}")
        print(f"   Engagement Rate:  {metrics.engagement_rate:.2f}%")
        print(f"   Collected At:     {metrics.collected_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if metrics.extra_data:
            print(f"\n   Extra Data:")
            for key, value in metrics.extra_data.items():
                print(f"      {key}: {value}")
    async def test_parser(
        self,
        platform: str,
        account_id: str,
        account_url: str
    ) -> Optional[PlatformMetrics]:
        self.print_header(f"Testing {platform.upper()} Parser")
        try:
            parser = ParserFactory.create(platform, account_id, account_url)
            self.print_info(f"Parser created: {parser.__class__.__name__}")
            self.print_info("Checking API availability...")
            is_available = await parser.is_available()
            if not is_available:
                self.print_error(f"{platform.upper()} API is not available")
                self.results[platform] = {
                    'status': 'unavailable',
                    'error': 'API not available'
                }
                return None
            self.print_success(f"{platform.upper()} API is available")
            self.print_info("Fetching metrics...")
            metrics = await parser.fetch_metrics()
            self.print_success("Metrics fetched successfully!")
            self.print_metrics(metrics)
            await parser.close()
            self.results[platform] = {
                'status': 'success',
                'metrics': metrics
            }
            return metrics
        except Exception as e:
            self.print_error(f"Failed to test {platform}: {str(e)}")
            self.results[platform] = {
                'status': 'error',
                'error': str(e)
            }
            return None
    async def run_tests(self, test_accounts: Dict[str, Dict[str, str]]) -> None:
        self.print_header("Social Media Parser Testing Suite")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for platform, account in test_accounts.items():
            await self.test_parser(
                platform=platform,
                account_id=account['account_id'],
                account_url=account['account_url']
            )
            print()
        self.print_summary()
    def print_summary(self) -> None:
        self.print_header("Test Summary")
        total = len(self.results)
        successful = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed = total - successful
        print(f"Total Parsers Tested: {total}")
        print(f"Successful:           {successful}")
        print(f"Failed:               {failed}")
        print()
        for platform, result in self.results.items():
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"{status_icon} {platform.upper()}: {result['status']}")
            if result['status'] == 'error':
                print(f"   Error: {result['error']}")
async def main():
    test_accounts = {
        'telegram': {
            'account_id': 'NIGINart_official',
            'account_url': 'https://t.me/NIGINart_official'
        },
        'youtube': {
            'account_id': 'UC8Qu8iMjh8nSNMYoBWHReAA',
            'account_url': 'https://www.youtube.com/channel/UC8Qu8iMjh8nSNMYoBWHReAA'
        }
    }
    tester = ParserTester()
    await tester.run_tests(test_accounts)
if __name__ == "__main__":
    asyncio.run(main())

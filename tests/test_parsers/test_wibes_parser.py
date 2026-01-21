import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.parsers.wibes_parser import WibesParser
from src.parsers.base import PlatformMetrics
@pytest.fixture
def parser():
    return WibesParser(
        account_id="288449",
        account_url="https://wibes.ru/author/288449"
    )
class TestWibesParserBasic:
    def test_get_platform_name(self, parser):
        assert parser.get_platform_name() == "wibes"
    def test_init(self, parser):
        assert parser.account_id == "288449"
        assert parser.account_url == "https://wibes.ru/author/288449"
        assert parser._browser is None
        assert parser._context is None
    def test_repr(self, parser):
        assert "WibesParser" in repr(parser)
        assert "288449" in repr(parser)
class TestWibesParserNumberParsing:
    def test_parse_plain_number(self, parser):
        assert parser._parse_number("1234") == 1234
        assert parser._parse_number("0") == 0
        assert parser._parse_number("999999") == 999999
    def test_parse_number_with_separators(self, parser):
        assert parser._parse_number("1 234") == 1234
        assert parser._parse_number("1,234") == 1234
        assert parser._parse_number("1 234 567") == 1234567
    def test_parse_number_with_k_suffix(self, parser):
        assert parser._parse_number("1.5K") == 1500
        assert parser._parse_number("1.5k") == 1500
        assert parser._parse_number("10K") == 10000
        assert parser._parse_number("1.5 тыс") == 1500
    def test_parse_number_with_m_suffix(self, parser):
        assert parser._parse_number("1M") == 1000000
        assert parser._parse_number("1.5M") == 1500000
        assert parser._parse_number("2.3 млн") == 2300000
    def test_parse_number_empty_or_invalid(self, parser):
        assert parser._parse_number("") is None
        assert parser._parse_number(None) is None
        assert parser._parse_number("abc") is None
    def test_parse_number_with_text(self, parser):
        assert parser._parse_number("123 подписчиков") == 123
        assert parser._parse_number("1.5K followers") == 1500
class TestWibesParserMocked:
    @pytest.mark.asyncio
    async def test_is_available_success(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                mock_page = MagicMock()
                mock_page.goto = AsyncMock(return_value=MagicMock(status=200))
                mock_page.content = AsyncMock(return_value="<html>Normal page</html>")
                mock_page.close = AsyncMock()
                mock_context = MagicMock()
                mock_context.new_page = AsyncMock(return_value=mock_page)
                parser._context = mock_context
                result = await parser.is_available()
                assert result is True
    @pytest.mark.asyncio
    async def test_is_available_blocked(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                mock_page = MagicMock()
                mock_page.goto = AsyncMock(return_value=MagicMock(status=200))
                mock_page.content = AsyncMock(return_value="<html>blocked captcha</html>")
                mock_page.close = AsyncMock()
                mock_context = MagicMock()
                mock_context.new_page = AsyncMock(return_value=mock_page)
                parser._context = mock_context
                result = await parser.is_available()
                assert result is False
    @pytest.mark.asyncio
    async def test_is_available_failure(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Connection failed")
            result = await parser.is_available()
            assert result is False
    @pytest.mark.asyncio
    async def test_fetch_metrics_success(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html>Normal page</html>")
            mock_page.close = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=None)
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.title = AsyncMock(return_value="Test Author | Wibes")
            mock_page.mouse = MagicMock()
            mock_page.mouse.move = AsyncMock()
            mock_page.evaluate = AsyncMock()
            mock_context = MagicMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            parser._context = mock_context
            with patch.object(parser, '_extract_author_name', new_callable=AsyncMock) as mock_name:
                mock_name.return_value = "Test Author"
                with patch.object(parser, '_extract_followers', new_callable=AsyncMock) as mock_followers:
                    mock_followers.return_value = 500
                    with patch.object(parser, '_extract_posts_count', new_callable=AsyncMock) as mock_posts_count:
                        mock_posts_count.return_value = 25
                        with patch.object(parser, '_extract_reactions', new_callable=AsyncMock) as mock_reactions:
                            mock_reactions.return_value = 150
                            with patch.object(parser, '_extract_posts', new_callable=AsyncMock) as mock_posts:
                                mock_posts.return_value = [
                                    {"title": "Post 1", "reactions": 50},
                                    {"title": "Post 2", "reactions": 100},
                                ]
                                with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                                    with patch.object(parser, '_simulate_human_behavior', new_callable=AsyncMock):
                                        metrics = await parser.fetch_metrics()
                                        assert isinstance(metrics, PlatformMetrics)
                                        assert metrics.platform == "wibes"
                                        assert metrics.account_id == "288449"
                                        assert metrics.followers == 500
                                        assert metrics.posts_count == 25
                                        assert metrics.total_shares == 150
                                        assert "author_name" in metrics.extra_data
                                        assert metrics.extra_data["author_name"] == "Test Author"
    @pytest.mark.asyncio
    async def test_fetch_metrics_bot_block(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html>498 blocked</html>")
            mock_page.close = AsyncMock()
            mock_context = MagicMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            parser._context = mock_context
            with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                with pytest.raises(Exception):
                    await parser.fetch_metrics()
    @pytest.mark.asyncio
    async def test_fetch_metrics_graceful_degradation(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html>Normal page</html>")
            mock_page.close = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=None)
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.title = AsyncMock(return_value="")
            mock_page.mouse = MagicMock()
            mock_page.mouse.move = AsyncMock()
            mock_page.evaluate = AsyncMock()
            mock_context = MagicMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            parser._context = mock_context
            with patch.object(parser, '_extract_author_name', new_callable=AsyncMock) as mock_name:
                mock_name.return_value = None
                with patch.object(parser, '_extract_followers', new_callable=AsyncMock) as mock_followers:
                    mock_followers.return_value = None
                    with patch.object(parser, '_extract_posts_count', new_callable=AsyncMock) as mock_posts_count:
                        mock_posts_count.return_value = None
                        with patch.object(parser, '_extract_reactions', new_callable=AsyncMock) as mock_reactions:
                            mock_reactions.return_value = None
                            with patch.object(parser, '_extract_posts', new_callable=AsyncMock) as mock_posts:
                                mock_posts.return_value = []
                                with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                                    with patch.object(parser, '_simulate_human_behavior', new_callable=AsyncMock):
                                        metrics = await parser.fetch_metrics()
                                        assert isinstance(metrics, PlatformMetrics)
                                        assert metrics.platform == "wibes"
                                        assert metrics.followers is None
                                        assert metrics.posts_count is None
    @pytest.mark.asyncio
    async def test_close_cleanup(self, parser):
        mock_context = MagicMock()
        mock_context.close = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        parser._context = mock_context
        parser._browser = mock_browser
        parser._playwright = mock_playwright
        await parser.close()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert parser._context is None
        assert parser._browser is None
        assert parser._playwright is None
class TestWibesParserSelectors:
    def test_follower_selectors_defined(self, parser):
        assert len(parser.FOLLOWER_SELECTORS) > 0
        assert all(isinstance(s, str) for s in parser.FOLLOWER_SELECTORS)
    def test_author_name_selectors_defined(self, parser):
        assert len(parser.AUTHOR_NAME_SELECTORS) > 0
        assert all(isinstance(s, str) for s in parser.AUTHOR_NAME_SELECTORS)
    def test_reactions_selectors_defined(self, parser):
        assert len(parser.REACTIONS_SELECTORS) > 0
        assert all(isinstance(s, str) for s in parser.REACTIONS_SELECTORS)
class TestWibesParserEngagementCalculation:
    @pytest.mark.asyncio
    async def test_engagement_rate_calculation(self, parser):
        with patch.object(parser, '_init_browser', new_callable=AsyncMock):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html>Normal</html>")
            mock_page.close = AsyncMock()
            mock_page.mouse = MagicMock()
            mock_page.mouse.move = AsyncMock()
            mock_page.evaluate = AsyncMock()
            mock_context = MagicMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            parser._context = mock_context
            with patch.object(parser, '_extract_author_name', new_callable=AsyncMock, return_value="Author"):
                with patch.object(parser, '_extract_followers', new_callable=AsyncMock, return_value=1000):
                    with patch.object(parser, '_extract_posts_count', new_callable=AsyncMock, return_value=10):
                        with patch.object(parser, '_extract_reactions', new_callable=AsyncMock, return_value=100):
                            with patch.object(parser, '_extract_posts', new_callable=AsyncMock, return_value=[]):
                                with patch.object(parser, '_human_delay', new_callable=AsyncMock):
                                    with patch.object(parser, '_simulate_human_behavior', new_callable=AsyncMock):
                                        metrics = await parser.fetch_metrics()
                                        assert metrics.engagement_rate == 10.0

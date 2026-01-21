import asyncio
import random
import re
from datetime import datetime
from typing import Optional, List, Dict
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
class DzenParser(BaseParser):
    PLATFORM_NAME = "dzen"
    BASE_URL = "https://dzen.ru"
    FOLLOWER_SELECTORS = [
        '[data-testid="subscriber-count"]',
        '.channel-info__subscribers',
        '.subscriber-count',
        'span[class*="subscriber"]',
        'div[class*="followers"] span',
    ]
    CHANNEL_NAME_SELECTORS = [
        '[data-testid="channel-name"]',
        '.channel-info__name',
        'h1[class*="title"]',
        '.channel-header__title',
    ]
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
    def get_platform_name(self) -> str:
        return self.PLATFORM_NAME
    async def is_available(self) -> bool:
        try:
            await self._init_browser()
            page = await self._context.new_page()
            try:
                response = await page.goto(
                    self.BASE_URL,
                    wait_until="domcontentloaded",
                    timeout=settings.playwright_timeout
                )
                return response is not None and response.status == 200
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"Dzen availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        async def _fetch() -> PlatformMetrics:
            await self._init_browser()
            page = await self._context.new_page()
            try:
                await self._human_delay(1.0, 2.0)
                logger.info(f"Navigating to Dzen channel: {self.account_url}")
                await page.goto(
                    self.account_url,
                    wait_until="networkidle",
                    timeout=settings.playwright_timeout
                )
                await self._human_delay(2.0, 4.0)
                await self._scroll_page(page)
                channel_name = await self._extract_channel_name(page)
                followers = await self._extract_followers(page)
                posts = await self._extract_posts(page)
                posts_count = len(posts)
                total_views = sum(p.get("views", 0) for p in posts)
                total_likes = sum(p.get("likes", 0) for p in posts)
                engagement_rate = 0.0
                if followers and followers > 0 and posts_count > 0:
                    avg_engagement = (total_views + total_likes) / posts_count
                    engagement_rate = round((avg_engagement / followers) * 100, 2)
                extra_data = {
                    "channel_name": channel_name,
                    "channel_id": self.account_id,
                    "posts_analyzed": posts_count,
                    "avg_views_per_post": round(total_views / posts_count, 2) if posts_count > 0 else 0,
                    "avg_likes_per_post": round(total_likes / posts_count, 2) if posts_count > 0 else 0,
                    "recent_posts": posts[:10],
                }
                logger.info(
                    f"Dzen metrics collected: followers={followers}, "
                    f"posts={posts_count}, views={total_views}, likes={total_likes}"
                )
                return PlatformMetrics(
                    platform=self.PLATFORM_NAME,
                    account_id=self.account_id,
                    collected_at=datetime.utcnow(),
                    followers=followers,
                    posts_count=posts_count,
                    total_views=total_views,
                    total_likes=total_likes,
                    total_comments=0,
                    total_shares=0,
                    engagement_rate=engagement_rate,
                    extra_data=extra_data
                )
            finally:
                await page.close()
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay,
            exceptions=(PlaywrightTimeout, ConnectionError, TimeoutError, Exception)
        )
    async def close(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.debug("Dzen parser resources cleaned up")
    async def _init_browser(self) -> None:
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        launch_options = {
            "headless": settings.playwright_headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        }
        if settings.proxy_url:
            launch_options["proxy"] = {"server": settings.proxy_url}
            logger.info(f"Using proxy: {settings.proxy_url}")
        self._browser = await self._playwright.chromium.launch(**launch_options)
        user_agent = random.choice(USER_AGENTS)
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(800, 1080)
        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": viewport_width, "height": viewport_height},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        logger.debug(f"Browser initialized with viewport {viewport_width}x{viewport_height}")
    async def _human_delay(self, min_sec: float, max_sec: float) -> None:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    async def _scroll_page(self, page: Page) -> None:
        try:
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await self._human_delay(0.5, 1.0)
            await page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(0.3, 0.5)
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
    async def _extract_channel_name(self, page: Page) -> Optional[str]:
        for selector in self.CHANNEL_NAME_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        try:
            title = await page.title()
            if title:
                return title.replace(" | Дзен", "").strip()
        except Exception:
            pass
        return None
    async def _extract_followers(self, page: Page) -> Optional[int]:
        for selector in self.FOLLOWER_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    count = self._parse_number(text)
                    if count is not None and count > 0:
                        return count
            except Exception:
                continue
        try:
            content = await page.content()
            patterns = [
                r'(\d[\d\s,\.]*)\s*подписчик',
                r'(\d[\d\s,\.]*)\s*subscriber',
                r'подписчик[а-я]*[:\s]+(\d[\d\s,\.]*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    count = self._parse_number(match.group(1))
                    if count is not None and count > 0:
                        return count
        except Exception as e:
            logger.warning(f"Fallback follower extraction failed: {e}")
        logger.warning("Could not extract followers from Dzen page")
        return None
    async def _extract_posts(self, page: Page) -> List[Dict]:
        posts = []
        try:
            post_selectors = [
                'article[class*="card"]',
                'div[class*="card-wrapper"]',
                'div[class*="feed-item"]',
                'div[class*="publication"]',
            ]
            post_elements = []
            for selector in post_selectors:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    post_elements = elements
                    break
            if not post_elements:
                logger.warning("Could not find post elements on Dzen page")
                return posts
            for element in post_elements[:20]:
                try:
                    post_data = await self._extract_post_data(element)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug(f"Failed to extract post data: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Posts extraction failed: {e}")
        return posts
    async def _extract_post_data(self, element) -> Optional[Dict]:
        post = {}
        try:
            title_selectors = ['h2', 'h3', '.title', '[class*="title"]']
            for selector in title_selectors:
                title_el = await element.query_selector(selector)
                if title_el:
                    post["title"] = (await title_el.inner_text()).strip()[:100]
                    break
            views_selectors = [
                '[class*="views"]',
                '[class*="view-count"]',
                'span[class*="stat"]',
            ]
            for selector in views_selectors:
                views_el = await element.query_selector(selector)
                if views_el:
                    text = await views_el.inner_text()
                    views = self._parse_number(text)
                    if views is not None:
                        post["views"] = views
                        break
            likes_selectors = [
                '[class*="like"]',
                '[class*="reaction"]',
                'button[class*="like"] span',
            ]
            for selector in likes_selectors:
                likes_el = await element.query_selector(selector)
                if likes_el:
                    text = await likes_el.inner_text()
                    likes = self._parse_number(text)
                    if likes is not None:
                        post["likes"] = likes
                        break
            post.setdefault("views", 0)
            post.setdefault("likes", 0)
            return post if post.get("title") or post.get("views", 0) > 0 else None
        except Exception:
            return None
    def _parse_number(self, text: str) -> Optional[int]:
        if not text:
            return None
        original_text = text.strip().lower()
        try:
            multiplier = 1
            if re.search(r'\d\s*k\b', original_text) or re.search(r'\d\s*к\b', original_text):
                multiplier = 1000
            elif re.search(r'\d\s*тыс', original_text):
                multiplier = 1000
            elif re.search(r'\d\s*m\b', original_text) or re.search(r'\d\s*млн', original_text):
                multiplier = 1000000
            numeric_match = re.search(r'(\d[\d\s]*[,.]?\d*)', original_text)
            if not numeric_match:
                return None
            numeric_str = numeric_match.group(1).strip()
            if re.match(r'^\d{1,3}(,\d{3})+$', numeric_str.replace(' ', '')):
                numeric_str = numeric_str.replace(' ', '').replace(',', '')
            elif ' ' in numeric_str:
                numeric_str = numeric_str.replace(' ', '')
            elif ',' in numeric_str and '.' not in numeric_str:
                parts = numeric_str.split(',')
                if len(parts) == 2 and len(parts[1]) == 3:
                    numeric_str = numeric_str.replace(',', '')
                else:
                    numeric_str = numeric_str.replace(',', '.')
            if '.' in numeric_str:
                return int(float(numeric_str) * multiplier)
            else:
                return int(numeric_str) * multiplier
        except (ValueError, TypeError):
            pass
        return None

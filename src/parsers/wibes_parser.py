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
class WibesParser(BaseParser):
    PLATFORM_NAME = "wibes"
    BASE_URL = "https://wibes.ru"
    FOLLOWER_SELECTORS = [
        '.author-subscribers',
        '.subscribers-count',
        '[class*="subscriber"]',
        '[class*="follower"]',
        'span[class*="count"]',
    ]
    AUTHOR_NAME_SELECTORS = [
        '.author-name',
        '.author-title',
        'h1[class*="name"]',
        '.profile-name',
    ]
    POST_COUNT_SELECTORS = [
        '.author-posts-count',
        '.publications-count',
        '[class*="posts-count"]',
        '[class*="publication"]',
    ]
    REACTIONS_SELECTORS = [
        '.author-reactions',
        '.reactions-count',
        '[class*="reaction"]',
        '[class*="like"]',
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
                await self._human_delay(1.0, 2.0)
                response = await page.goto(
                    self.BASE_URL,
                    wait_until="domcontentloaded",
                    timeout=settings.playwright_timeout
                )
                content = await page.content()
                if "blocked" in content.lower() or "captcha" in content.lower():
                    logger.warning("Wibes returned a block/captcha page")
                    return False
                return response is not None and response.status == 200
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"Wibes availability check failed: {e}")
            return False
    async def fetch_metrics(self) -> PlatformMetrics:
        async def _fetch() -> PlatformMetrics:
            await self._init_browser()
            page = await self._context.new_page()
            try:
                await self._human_delay(2.0, 4.0)
                logger.info(f"Navigating to Wibes author: {self.account_url}")
                await page.goto(
                    self.account_url,
                    wait_until="networkidle",
                    timeout=settings.playwright_timeout
                )
                content = await page.content()
                if "498" in content or "blocked" in content.lower():
                    raise RuntimeError("Wibes returned bot block page (498)")
                await self._human_delay(3.0, 5.0)
                await self._simulate_human_behavior(page)
                author_name = await self._extract_author_name(page)
                followers = await self._extract_followers(page)
                posts_count = await self._extract_posts_count(page)
                reactions = await self._extract_reactions(page)
                posts = await self._extract_posts(page)
                engagement_rate = 0.0
                if followers and followers > 0 and reactions:
                    engagement_rate = round((reactions / followers) * 100, 2)
                extra_data = {
                    "author_name": author_name,
                    "author_id": self.account_id,
                    "total_reactions": reactions,
                    "posts_analyzed": len(posts),
                    "recent_posts": posts[:10],
                }
                if posts:
                    total_post_reactions = sum(p.get("reactions", 0) for p in posts)
                    extra_data["avg_reactions_per_post"] = round(
                        total_post_reactions / len(posts), 2
                    ) if len(posts) > 0 else 0
                logger.info(
                    f"Wibes metrics collected: followers={followers}, "
                    f"posts={posts_count}, reactions={reactions}"
                )
                return PlatformMetrics(
                    platform=self.PLATFORM_NAME,
                    account_id=self.account_id,
                    collected_at=datetime.utcnow(),
                    followers=followers,
                    posts_count=posts_count,
                    total_views=0,
                    total_likes=reactions,
                    total_comments=0,
                    total_shares=reactions,
                    engagement_rate=engagement_rate,
                    extra_data=extra_data
                )
            finally:
                await page.close()
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts + 2,
            initial_delay=settings.parser_retry_delay * 2,
            exceptions=(PlaywrightTimeout, ConnectionError, TimeoutError, RuntimeError, Exception)
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
        logger.debug("Wibes parser resources cleaned up")
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
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
            ]
        }
        if settings.proxy_url:
            launch_options["proxy"] = {"server": settings.proxy_url}
            logger.info(f"Using proxy: {settings.proxy_url}")
        self._browser = await self._playwright.chromium.launch(**launch_options)
        user_agent = random.choice(USER_AGENTS)
        viewport_width = random.randint(1366, 1920)
        viewport_height = random.randint(768, 1080)
        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": viewport_width, "height": viewport_height},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )
        await self._context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
            // Override chrome property
            window.chrome = {
                runtime: {}
            };
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        logger.debug(f"Wibes browser initialized with stealth mode, viewport {viewport_width}x{viewport_height}")
    async def _human_delay(self, min_sec: float, max_sec: float) -> None:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    async def _simulate_human_behavior(self, page: Page) -> None:
        try:
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await self._human_delay(0.1, 0.3)
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await self._human_delay(0.5, 1.0)
            await page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(0.3, 0.5)
        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")
    async def _extract_author_name(self, page: Page) -> Optional[str]:
        for selector in self.AUTHOR_NAME_SELECTORS:
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
                return title.split("|")[0].strip()
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
                    if count is not None and count >= 0:
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
                    if count is not None and count >= 0:
                        return count
        except Exception as e:
            logger.debug(f"Fallback follower extraction failed: {e}")
        logger.warning("Could not extract followers from Wibes page")
        return None
    async def _extract_posts_count(self, page: Page) -> Optional[int]:
        for selector in self.POST_COUNT_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    count = self._parse_number(text)
                    if count is not None and count >= 0:
                        return count
            except Exception:
                continue
        try:
            post_elements = await page.query_selector_all('article, .post, .publication, [class*="post-item"]')
            if post_elements:
                return len(post_elements)
        except Exception:
            pass
        return None
    async def _extract_reactions(self, page: Page) -> Optional[int]:
        for selector in self.REACTIONS_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    count = self._parse_number(text)
                    if count is not None and count >= 0:
                        return count
            except Exception:
                continue
        try:
            reaction_elements = await page.query_selector_all('[class*="reaction"] span, [class*="like"] span')
            total = 0
            for el in reaction_elements:
                text = await el.inner_text()
                count = self._parse_number(text)
                if count:
                    total += count
            if total > 0:
                return total
        except Exception:
            pass
        return None
    async def _extract_posts(self, page: Page) -> List[Dict]:
        posts = []
        try:
            post_selectors = [
                'article',
                '.post',
                '.publication',
                '[class*="post-item"]',
                '[class*="feed-item"]',
            ]
            post_elements = []
            for selector in post_selectors:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    post_elements = elements
                    break
            if not post_elements:
                return posts
            for element in post_elements[:15]:
                try:
                    post_data = await self._extract_post_data(element)
                    if post_data:
                        posts.append(post_data)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Posts extraction failed: {e}")
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
            reaction_selectors = ['[class*="reaction"]', '[class*="like"]', '.reactions']
            for selector in reaction_selectors:
                reaction_el = await element.query_selector(selector)
                if reaction_el:
                    text = await reaction_el.inner_text()
                    reactions = self._parse_number(text)
                    if reactions is not None:
                        post["reactions"] = reactions
                        break
            post.setdefault("reactions", 0)
            return post if post.get("title") or post.get("reactions", 0) > 0 else None
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

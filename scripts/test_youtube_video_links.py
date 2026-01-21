import asyncio
import sys
import io
import re
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
async def test_video_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        try:
            print("[*] Navigating to dashboard...")
            await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)
            print("[*] Clicking YouTube page...")
            await page.locator('a:has-text("YouTube")').click()
            await asyncio.sleep(8)
            print("\n[*] Looking for 'Последние видео' section...")
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(1)
                recent_videos_heading = page.locator('text="Последние видео"')
                if await recent_videos_heading.count() > 0:
                    print(f"[FOUND] 'Последние видео' at scroll {i}")
                    await recent_videos_heading.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    break
            print("\n[*] Extracting YouTube video links...")
            all_links = await page.locator('a[href*="youtube.com"]').all()
            video_links = []
            for link in all_links:
                href = await link.get_attribute('href')
                if href and '/watch?v=' in href:
                    video_links.append(href)
            print(f"[INFO] Found {len(video_links)} YouTube video links")
            if video_links:
                print("\n[*] Analyzing video IDs...")
                print("=" * 80)
                valid_pattern = re.compile(r'^[A-Za-z0-9_-]{10}[AEIMQUYcgkosw048]$')
                for i, link in enumerate(video_links[:10], 1):
                    match = re.search(r'[?&]v=([A-Za-z0-9_-]+)', link)
                    if match:
                        video_id = match.group(1)
                        is_valid = bool(valid_pattern.match(video_id))
                        status = "✅ VALID" if is_valid else "❌ INVALID"
                        print(f"{i}. {status} | video_id: {video_id} | length: {len(video_id)}")
                        print(f"   URL: {link}")
                        if not is_valid:
                            print(f"   ⚠️  PROBLEM: Last char '{video_id[-1]}' is not in [AEIMQUYcgkosw048]")
                    else:
                        print(f"{i}. ❌ FAILED to extract video_id from: {link}")
                    print()
                print("=" * 80)
            else:
                print("[WARN] No video links found on the page")
            await page.screenshot(path=".playwright-mcp/youtube_video_links_test.png", full_page=True)
            print("\n[OK] Screenshot saved")
            return len(video_links) > 0
        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=".playwright-mcp/youtube_links_error.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_video_links())
    print(f"\n{'✅ SUCCESS' if result else '❌ FAILED'}")

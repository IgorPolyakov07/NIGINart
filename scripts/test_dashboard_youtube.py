import asyncio
import sys
from playwright.async_api import async_playwright
async def test_youtube_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            print("[*] Navigating to dashboard...")
            await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            print("[*] Clicking YouTube page link...")
            youtube_link = page.locator('a:has-text("YouTube")')
            if await youtube_link.count() > 0:
                await youtube_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot...")
                await page.screenshot(path=".playwright-mcp/youtube_page_test.png", full_page=True)
                error_locator = page.locator('text=/KeyError|Traceback|Error/')
                error_count = await error_locator.count()
                if error_count > 0:
                    print(f"[FAIL] Found {error_count} errors on the page!")
                    errors = await error_locator.all_text_contents()
                    for i, error in enumerate(errors, 1):
                        print(f"   Error {i}: {error[:200]}")
                    return False
                else:
                    print("[PASS] No errors found on YouTube page!")
                    top_videos_section = page.locator('text="Топ видео"')
                    if await top_videos_section.count() > 0:
                        print("[PASS] 'Top videos' section found!")
                    else:
                        print("[WARN] 'Top videos' section not found (might be no data yet)")
                    return True
            else:
                print("[FAIL] YouTube link not found in sidebar!")
                return False
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            await page.screenshot(path=".playwright-mcp/youtube_page_error.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_youtube_page())
    sys.exit(0 if result else 1)

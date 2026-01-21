import asyncio
import sys
import io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
async def test_video_sections():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        try:
            print("[*] Navigating to dashboard...")
            await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)
            print("[*] Clicking YouTube page...")
            youtube_link = page.locator('a:has-text("YouTube")')
            if await youtube_link.count() > 0:
                await youtube_link.click()
                await asyncio.sleep(8)
                print("[*] Taking full page screenshot...")
                await page.screenshot(path=".playwright-mcp/youtube_full_current.png", full_page=True)
                print("\n[*] Looking for video sections...")
                for i in range(5):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)
                    recent_videos_header = page.locator('text=/Последние видео/i')
                    if await recent_videos_header.count() > 0:
                        print("[FOUND] 'Последние видео' section found at scroll position", i)
                        await recent_videos_header.scroll_into_view_if_needed()
                        await asyncio.sleep(2)
                        await page.screenshot(path=".playwright-mcp/recent_videos_section.png")
                        tables_count = await page.locator('table').count()
                        print(f"[INFO] Total tables on page: {tables_count}")
                        no_data_msg = page.locator('text=/Нет данных о последних видео/i')
                        if await no_data_msg.count() > 0:
                            print("[WARN] 'Нет данных о последних видео' message found")
                        else:
                            print("[OK] No 'No data' message - videos should be displayed")
                        break
                print("\n[*] Looking for Top Videos section...")
                for i in range(5):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)
                    top_videos_header = page.locator('text=/Топ видео/i')
                    if await top_videos_header.count() > 0:
                        print("[FOUND] 'Топ видео' section found at scroll position", i)
                        await top_videos_header.scroll_into_view_if_needed()
                        await asyncio.sleep(2)
                        await page.screenshot(path=".playwright-mcp/top_videos_section.png")
                        selectboxes = await page.locator('[data-baseweb="select"]').count()
                        print(f"[INFO] Found {selectboxes} selectboxes (for sorting)")
                        break
                print("\n[*] Analyzing page content...")
                page_text = await page.text_content('body')
                if 'Просмотры' in page_text and 'Лайки' in page_text and 'Комментарии' in page_text:
                    print("[OK] Video metrics columns found")
                else:
                    print("[WARN] Video metrics columns not found")
                if 'Средние просмотры на видео' in page_text:
                    print("[OK] Average views metric found")
                else:
                    print("[WARN] Average views metric not found")
                errors = await page.locator('text=/KeyError|Traceback|Error|Exception/').count()
                if errors > 0:
                    print(f"[FAIL] Found {errors} errors on page")
                    await page.screenshot(path=".playwright-mcp/youtube_errors_found.png", full_page=True)
                else:
                    print("[OK] No errors found")
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(2)
                await page.screenshot(path=".playwright-mcp/youtube_complete_test.png", full_page=True)
                print("\n[SUCCESS] Test completed! Screenshots saved to .playwright-mcp/")
                return True
            else:
                print("[FAIL] YouTube link not found")
                return False
        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=".playwright-mcp/youtube_test_exception.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_video_sections())
    print(f"\n{'✅ SUCCESS' if result else '❌ FAILED'}")

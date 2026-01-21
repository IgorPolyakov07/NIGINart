import asyncio
from playwright.async_api import async_playwright
async def test_youtube_detailed():
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
                await page.screenshot(path=".playwright-mcp/youtube_full_page.png", full_page=True)
                print("\n[*] Checking page sections...")
                kpi_cards = await page.locator('[data-testid="stMetric"]').count()
                print(f"[INFO] Found {kpi_cards} KPI cards")
                charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {charts} charts")
                recent_videos = page.locator('text="Последние видео"')
                if await recent_videos.count() > 0:
                    print("[PASS] 'Последние видео' section found")
                    await recent_videos.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    await page.screenshot(path=".playwright-mcp/youtube_recent_videos.png")
                else:
                    print("[FAIL] 'Последние видео' section NOT found")
                top_videos = page.locator('text="Топ видео"')
                if await top_videos.count() > 0:
                    print("[PASS] 'Топ видео' section found")
                    await top_videos.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    await page.screenshot(path=".playwright-mcp/youtube_top_videos.png")
                else:
                    print("[FAIL] 'Топ видео' section NOT found")
                no_data = page.locator('text="Нет данных о последних видео"')
                if await no_data.count() > 0:
                    print("[WARN] 'Нет данных о последних видео' message found")
                    await no_data.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    await page.screenshot(path=".playwright-mcp/youtube_no_data_warning.png")
                print("\n[*] Analyzing page content...")
                page_text = await page.text_content('body')
                if 'Подписчики' in page_text:
                    print("[PASS] Subscriber count section found")
                if 'Всего видео' in page_text:
                    print("[PASS] Total videos section found")
                if 'Engagement' in page_text or 'Вовлеченность' in page_text:
                    print("[PASS] Engagement metrics found")
                error_count = await page.locator('text=/KeyError|Traceback|Error/').count()
                if error_count > 0:
                    print(f"[FAIL] Found {error_count} errors")
                    await page.screenshot(path=".playwright-mcp/youtube_errors.png")
                else:
                    print("[PASS] No errors found")
                print("\n[SUCCESS] Test completed. Screenshots saved to .playwright-mcp/")
                return True
            else:
                print("[FAIL] YouTube link not found")
                return False
        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            await page.screenshot(path=".playwright-mcp/youtube_exception.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_youtube_detailed())

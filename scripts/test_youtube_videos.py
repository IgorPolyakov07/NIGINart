import asyncio
from playwright.async_api import async_playwright
async def test_youtube_videos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        try:
            print("[*] Navigating to dashboard...")
            await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)
            print("[*] Clicking YouTube page...")
            youtube_link = page.locator('a').filter(has_text="YouTube")
            await youtube_link.click()
            await asyncio.sleep(8)
            print("[*] Full page screenshot...")
            await page.screenshot(path=".playwright-mcp/youtube_test_full.png", full_page=True)
            print("\n[CHECK] KPI Cards...")
            subscribers = page.locator('text=/Подписчики/')
            if await subscribers.count() > 0:
                print("[OK] Subscribers metric found")
            videos_count = page.locator('text=/Всего видео/')
            if await videos_count.count() > 0:
                print("[OK] Videos count metric found")
            print("\n[CHECK] Recent Videos section...")
            await asyncio.sleep(2)
            tables = await page.locator('table').count()
            print(f"[INFO] Found {tables} tables on page")
            no_data_msg = page.locator('text=/Нет данных/')
            if await no_data_msg.count() > 0:
                print("[WARN] 'No data' message found - taking screenshot")
                await page.screenshot(path=".playwright-mcp/youtube_no_data.png", full_page=True)
            else:
                print("[OK] No 'No data' messages")
            print("\n[CHECK] Scrolling through sections...")
            tabs = page.locator('[role="tab"]')
            tab_count = await tabs.count()
            print(f"[INFO] Found {tab_count} tabs")
            if tab_count > 0:
                for i in range(min(tab_count, 3)):
                    print(f"[INFO] Clicking tab {i+1}...")
                    await tabs.nth(i).click()
                    await asyncio.sleep(2)
                    await page.screenshot(path=f".playwright-mcp/youtube_tab_{i+1}.png", full_page=True)
            print("\n[*] Final screenshot...")
            await page.screenshot(path=".playwright-mcp/youtube_final.png", full_page=True)
            print("\n[SUCCESS] Test completed!")
            print("Screenshots saved in .playwright-mcp/")
            print("\nBrowser will close in 10 seconds...")
            await asyncio.sleep(10)
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path=".playwright-mcp/youtube_error.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    asyncio.run(test_youtube_videos())

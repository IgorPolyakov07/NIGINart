import asyncio
import sys
import io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
async def test_graphs_detailed():
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
            print("\n[*] Scrolling to 'Динамика показателей'...")
            dynamics_tab = page.locator('text="Динамика"')
            if await dynamics_tab.count() > 0:
                await dynamics_tab.click()
                await asyncio.sleep(3)
                print("[OK] Clicked 'Динамика' tab")
            for i in range(3):
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(1)
            print("\n[*] Looking for 'Динамика подписчиков' graph...")
            subscriber_heading = page.locator('text="Динамика подписчиков"')
            if await subscriber_heading.count() > 0:
                print("[FOUND] 'Динамика подписчиков' found")
                await subscriber_heading.scroll_into_view_if_needed()
                await asyncio.sleep(2)
                element = await subscriber_heading.element_handle()
                if element:
                    await element.screenshot(path=".playwright-mcp/dynamics_subscribers_heading.png")
                await page.evaluate("window.scrollBy(0, 200)")
                await asyncio.sleep(2)
                await page.screenshot(path=".playwright-mcp/dynamics_subscribers_graph.png")
                print("[OK] Saved 'Динамика подписчиков' screenshot")
            print("\n[*] Looking for 'Прирост подписчиков' section...")
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(1)
                growth_heading = page.locator('text="Прирост подписчиков"')
                if await growth_heading.count() > 0:
                    print(f"[FOUND] 'Прирост подписчиков' found at scroll {i}")
                    await growth_heading.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    await page.screenshot(path=".playwright-mcp/dynamics_subscriber_growth.png")
                    print("[OK] Saved 'Прирост подписчиков' screenshot")
                    break
            else:
                print("[WARN] 'Прирост подписчиков' not found after scrolling")
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            await page.screenshot(path=".playwright-mcp/youtube_dynamics_full.png", full_page=True)
            print("\n[OK] Saved full page screenshot")
            print("\n✅ Test completed! Check .playwright-mcp/ for screenshots")
            return True
        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=".playwright-mcp/youtube_graphs_error.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_graphs_detailed())

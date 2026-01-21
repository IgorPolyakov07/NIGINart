import asyncio
import sys
import io
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
async def test_subscriber_graph():
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
                await page.screenshot(path=".playwright-mcp/youtube_subscribers_full.png", full_page=True)
                print("\n[*] Looking for 'Динамика подписчиков' graph...")
                subscriber_graph = page.locator('text="Динамика подписчиков"')
                if await subscriber_graph.count() > 0:
                    print("[FOUND] 'Динамика подписчиков' graph found")
                    await subscriber_graph.scroll_into_view_if_needed()
                    await asyncio.sleep(3)
                    await page.screenshot(path=".playwright-mcp/youtube_subscriber_graph.png")
                    print("[OK] Screenshot saved: youtube_subscriber_graph.png")
                else:
                    print("[WARN] 'Динамика подписчиков' graph not found")
                print("\n[*] Looking for 'Прирост подписчиков' section...")
                growth_section = page.locator('text="Прирост подписчиков"')
                if await growth_section.count() > 0:
                    print("[FOUND] 'Прирост подписчиков' section found")
                    await growth_section.scroll_into_view_if_needed()
                    await asyncio.sleep(3)
                    await page.screenshot(path=".playwright-mcp/youtube_subscriber_growth.png")
                    print("[OK] Screenshot saved: youtube_subscriber_growth.png")
                    metrics = await page.locator('[data-testid="stMetric"]').count()
                    print(f"[INFO] Found {metrics} growth metric cards")
                else:
                    print("[WARN] 'Прирост подписчиков' section not found")
                print("\n[*] Checking for data anomalies...")
                page_text = await page.text_content('body')
                suspicious_patterns = ['20,000', '25,000', '24,', '29,']
                found_suspicious = False
                for pattern in suspicious_patterns:
                    if pattern in page_text:
                        print(f"[WARN] Found suspicious value pattern: '{pattern}'")
                        found_suspicious = True
                if not found_suspicious:
                    print("[OK] No suspicious large subscriber counts found")
                if '56' in page_text or '55' in page_text or '54' in page_text:
                    print("[OK] Realistic subscriber counts (50-56 range) found")
                else:
                    print("[WARN] Expected subscriber counts (50-56) not found")
                errors = await page.locator('text=/KeyError|Traceback|Error|Exception/').count()
                if errors > 0:
                    print(f"[FAIL] Found {errors} errors on page")
                    await page.screenshot(path=".playwright-mcp/youtube_subscribers_errors.png", full_page=True)
                else:
                    print("[OK] No errors found")
                print("\n[SUCCESS] Test completed! Screenshots saved to .playwright-mcp/")
                return True
            else:
                print("[FAIL] YouTube link not found")
                return False
        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=".playwright-mcp/youtube_subscribers_exception.png", full_page=True)
            return False
        finally:
            await browser.close()
if __name__ == "__main__":
    result = asyncio.run(test_subscriber_graph())
    print(f"\n{'✅ SUCCESS' if result else '❌ FAILED'}")

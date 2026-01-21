import asyncio
import sys
from playwright.async_api import async_playwright
async def test_dashboard_charts():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        results = {"passed": [], "failed": [], "warnings": []}
        try:
            print("[*] Navigating to dashboard home page...")
            await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)
            print("[*] Taking screenshot of home page...")
            await page.screenshot(path=".playwright-mcp/dashboard_home.png", full_page=True)
            print("[*] Checking for charts on home page...")
            charts = await page.locator('[data-testid="stPlotlyChart"]').count()
            print(f"[INFO] Found {charts} Plotly charts on home page")
            if charts > 0:
                results["passed"].append(f"Home page: Found {charts} charts")
            else:
                results["warnings"].append("Home page: No charts found")
            print("\n[*] Testing YouTube page...")
            youtube_link = page.locator('a:has-text("YouTube")')
            if await youtube_link.count() > 0:
                await youtube_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot of YouTube page...")
                await page.screenshot(path=".playwright-mcp/youtube_charts.png", full_page=True)
                youtube_charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {youtube_charts} charts on YouTube page")
                if youtube_charts > 0:
                    results["passed"].append(f"YouTube: Found {youtube_charts} charts")
                else:
                    results["failed"].append("YouTube: No charts found")
                errors = await page.locator('text=/KeyError|Traceback|Error/').count()
                if errors == 0:
                    results["passed"].append("YouTube: No errors detected")
                else:
                    results["failed"].append(f"YouTube: Found {errors} errors")
            print("\n[*] Testing Telegram page...")
            telegram_link = page.locator('a:has-text("Telegram")')
            if await telegram_link.count() > 0:
                await telegram_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot of Telegram page...")
                await page.screenshot(path=".playwright-mcp/telegram_charts.png", full_page=True)
                telegram_charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {telegram_charts} charts on Telegram page")
                if telegram_charts > 0:
                    results["passed"].append(f"Telegram: Found {telegram_charts} charts")
                else:
                    results["warnings"].append("Telegram: No charts found (might be no data)")
            print("\n[*] Testing Instagram page...")
            instagram_link = page.locator('a:has-text("Instagram")')
            if await instagram_link.count() > 0:
                await instagram_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot of Instagram page...")
                await page.screenshot(path=".playwright-mcp/instagram_charts.png", full_page=True)
                instagram_charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {instagram_charts} charts on Instagram page")
                if instagram_charts > 0:
                    results["passed"].append(f"Instagram: Found {instagram_charts} charts")
                else:
                    results["warnings"].append("Instagram: No charts found")
            print("\n[*] Testing TikTok page...")
            tiktok_link = page.locator('a:has-text("TikTok")')
            if await tiktok_link.count() > 0:
                await tiktok_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot of TikTok page...")
                await page.screenshot(path=".playwright-mcp/tiktok_charts.png", full_page=True)
                tiktok_charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {tiktok_charts} charts on TikTok page")
                if tiktok_charts > 0:
                    results["passed"].append(f"TikTok: Found {tiktok_charts} charts")
                else:
                    results["warnings"].append("TikTok: No charts found")
            print("\n[*] Testing VK page...")
            vk_link = page.locator('a:has-text("VK")')
            if await vk_link.count() > 0:
                await vk_link.click()
                await asyncio.sleep(5)
                print("[*] Taking screenshot of VK page...")
                await page.screenshot(path=".playwright-mcp/vk_charts.png", full_page=True)
                vk_charts = await page.locator('[data-testid="stPlotlyChart"]').count()
                print(f"[INFO] Found {vk_charts} charts on VK page")
                if vk_charts > 0:
                    results["passed"].append(f"VK: Found {vk_charts} charts")
                else:
                    results["warnings"].append("VK: No charts found")
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            results["failed"].append(f"Exception: {e}")
            await page.screenshot(path=".playwright-mcp/error.png", full_page=True)
        finally:
            await browser.close()
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        if results["passed"]:
            print(f"\n[PASS] {len(results['passed'])} tests passed:")
            for test in results["passed"]:
                print(f"  + {test}")
        if results["warnings"]:
            print(f"\n[WARN] {len(results['warnings'])} warnings:")
            for test in results["warnings"]:
                print(f"  ? {test}")
        if results["failed"]:
            print(f"\n[FAIL] {len(results['failed'])} tests failed:")
            for test in results["failed"]:
                print(f"  - {test}")
            return False
        print("\n[SUCCESS] All critical tests passed!")
        return True
if __name__ == "__main__":
    result = asyncio.run(test_dashboard_charts())
    sys.exit(0 if result else 1)

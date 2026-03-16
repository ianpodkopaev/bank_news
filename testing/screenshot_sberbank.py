#!/usr/bin/env python3
"""Screenshot Sberbank page to see what it looks like"""

import asyncio
from playwright.async_api import async_playwright
import sys
from datetime import datetime

async def main():
    url = "https://www.sberbank.ru/ru/sberpress/all"

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        # Create context with realistic settings
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        # Create page
        page = await context.new_page()

        # Stealth script to hide automation
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
        """)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to: {url}")

        # Navigate to page
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Page loaded, waiting 10s for JavaScript challenge...")
            await asyncio.sleep(10)

            # Wait for body to be populated
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for content to appear...")
            try:
                await page.wait_for_selector("body", timeout=60000)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Body element found")
            except:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Timeout waiting for body, proceeding anyway")

            # Wait additional time for challenge completion
            await asyncio.sleep(5)

            # Check if we're still on challenge page
            content = await page.content()
            if "TSPD" in content and "Please enable JavaScript" in content:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Still on TSPD challenge page")
            elif "Возникла проблема при открытии сайта" in content:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Blocked by WAF")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: Page appears to be loaded")

            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/confuseduser/GolandProjects/bank_news/sberbank_screenshot_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Screenshot saved: {screenshot_path}")

            # Save HTML
            html_path = f"/home/confuseduser/GolandProjects/bank_news/sberbank_html_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] HTML saved: {html_path}")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        finally:
            await browser.close()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Browser closed")

if __name__ == "__main__":
    asyncio.run(main())

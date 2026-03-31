#!/usr/bin/env python3
"""
Test a website for:
- robots.txt accessibility
- Basic HTTP response
- JavaScript rendering challenges (TSPD, etc.)
- Take a screenshot
"""

import asyncio
import sys
from urllib.parse import urlparse
from datetime import datetime
import requests
from playwright.async_api import async_playwright

async def test_website(url):
    """Test a single website"""
    print(f"\n{'='*70}")
    print(f"Testing: {url}")
    print(f"{'='*70}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Parse URL
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    base_domain = parsed.netloc.replace('.', '_')

    # Test 1: robots.txt
    print(f"\n[{timestamp}] Test 1: Checking robots.txt")
    try:
        response = requests.get(robots_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        if response.status_code == 200:
            print(f" robots.txt found (status: {response.status_code})")
            print(f"Content preview:\n{response.text[:500]}")
        else:
            print(f" robots.txt not accessible (status: {response.status_code})")
    except Exception as e:
        print(f" Error accessing robots.txt: {str(e)}")

    # Test 2: Basic HTTP response
    print(f"\n[{timestamp}] Test 2: Basic HTTP GET request")
    print(f"\n Copy this command to manually test in your terminal:")
    print(f"   curl -v -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' '{url}' | head -100")
    print()

    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)} characters")
        print(f"Content preview:\n{response.text[:500]}")

        # Check for TSPD
        if "TSPD" in response.text:
            print(f"  TSPD detected in HTTP response")
        if "Please enable JavaScript" in response.text:
            print(f"  JavaScript challenge detected")
        if "Возникла проблема при открытии сайта" in response.text:
            print(f"  WAF blocking detected")
    except Exception as e:
        print(f" Error: {str(e)}")

    # Test 3: Playwright rendering
    print(f"\n[{timestamp}] Test 3: JavaScript rendering with Playwright")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
            )
            page = await context.new_page()

            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for potential challenges
            await asyncio.sleep(10)

            content = await page.content()
            print(f"Rendered content length: {len(content)} characters")
            print(f"Content preview:\n{content[:500]}")

            # Check for challenges
            if "TSPD" in content and "Please enable JavaScript" in content:
                print(f" JS Challenge: Still on TSPD challenge page after rendering")
            elif "Возникла проблема при открытии сайта" in content:
                print(f" WAF: Blocked after rendering")
            else:
                print(f" JS Rendering: Page loaded successfully")

            # Screenshot
            screenshot_path = f"test_{base_domain}_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f" Screenshot saved: {screenshot_path}")

            # Save HTML
            html_path = f"test_{base_domain}_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f" HTML saved: {html_path}")

            await browser.close()

    except Exception as e:
        print(f" Playwright error: {str(e)}")

    print(f"\n{'='*70}")
    print(f"Test complete: {url}")
    print(f"{'='*70}\n")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_website.py <URL1> [URL2] [URL3] ...")
        print("\nExample:")
        print("  python3 test_website.py https://bankinform.ru/news")
        print("  python3 test_website.py https://myfin.by https://bankinform.ru/news")
        sys.exit(1)

    urls = sys.argv[1:]
    print(f"Testing {len(urls)} website(s)...")

    for url in urls:
        await test_website(url)

if __name__ == "__main__":
    asyncio.run(main())

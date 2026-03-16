import scrapy
from urllib.parse import urljoin
import re
from datetime import datetime, timedelta
from scrapy.http import HtmlResponse
import json


class TbankSpider(scrapy.Spider):
    name = 'tbank'
    allowed_domains = ['tbank.ru', 'www.tbank.ru']

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
        },
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    }

    def __init__(self, *args, **kwargs):
        super(TbankSpider, self).__init__(*args, **kwargs)
        self.lookback_days = 30
        self.max_pages = 10
        self.today = datetime.now()
        self.date_threshold = datetime.now() - timedelta(days=self.lookback_days)
        self.logger.info(
            f"Date threshold: {self.date_threshold.strftime('%d.%m.%Y')} (looking back {self.lookback_days} days)")
        self.processed_urls = set()

    # Russian month mapping for date parsing
    RU_MONTHS = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    def start_requests(self):
        """Start with the main news page"""
        url = "https://www.tbank.ru/about/news/"
        yield scrapy.Request(
            url=url,
            callback=self.parse_main_page,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "tbank_news",
                "wait_until": "domcontentloaded",
                "page": 1
            },
            errback=self.close_page_on_error
        )

    async def parse_main_page(self, response):
        """Parse main news page and extract article links"""
        page = response.meta["playwright_page"]

        try:
            # Wait for content to load (equivalent to asyncio.sleep(30) in original)
            await page.wait_for_timeout(30000)  # 30 seconds

            self.logger.info("Page loaded, searching for article links...")

            # Method 1: Try copy link elements
            copy_links = await page.query_selector_all('[data-test="article_copyLink"]')
            self.logger.info(f"Found {len(copy_links)} copy link elements")

            # Method 2: Also try anchor tags
            anchor_links = await page.query_selector_all('a[href*="/about/news/"]')
            self.logger.info(f"Found {len(anchor_links)} anchor links")

            # Extract URLs from copy link elements
            article_urls = set()

            for link_elem in copy_links:
                try:
                    text = await link_elem.inner_text()
                    if text and 'tbank.ru/about/news/' in text:
                        url = text.strip()
                        if not url.startswith('http'):
                            url = f"https://{url}"
                        article_urls.add(url)
                except Exception as e:
                    self.logger.warning(f"Error extracting copy link: {e}")

            # Extract URLs from anchor tags
            for link_elem in anchor_links:
                try:
                    href = await link_elem.get_attribute('href')
                    if href and href not in ['/about/news/', 'https://www.tbank.ru/about/news/']:
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = f"https://www.tbank.ru{href}"
                            else:
                                href = f"https://www.tbank.ru/{href}"
                        article_urls.add(href)
                except Exception as e:
                    self.logger.warning(f"Error extracting anchor link: {e}")

            self.logger.info(f"Total unique article links found: {len(article_urls)}")

            # Process each article URL
            for article_url in article_urls:
                if article_url in self.processed_urls:
                    self.logger.info(f"Skipping duplicate URL: {article_url}")
                    continue

                self.processed_urls.add(article_url)

                # Navigate to article page
                yield scrapy.Request(
                    url=article_url,
                    callback=self.parse_article,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context": "tbank_article",
                        "wait_until": "domcontentloaded",
                        "article_url": article_url
                    },
                    errback=self.close_page_on_error
                )

            # Handle pagination if needed (max_pages limit)
            current_page = response.meta.get('page', 1)
            if current_page < self.max_pages:
                # Look for next page link/button
                next_button = await page.query_selector(
                    'a[aria-label="Next"], button[aria-label="Next"], .pagination-next')
                if next_button:
                    await next_button.click()
                    await page.wait_for_timeout(5000)  # Wait for next page to load

                    next_page_url = page.url
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse_main_page,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_context": "tbank_news",
                            "wait_until": "domcontentloaded",
                            "page": current_page + 1
                        },
                        errback=self.close_page_on_error
                    )

        finally:
            # Always close the page to free resources
            await page.close()

    async def parse_article(self, response):
        """Parse individual article page"""
        page = response.meta["playwright_page"]
        article_url = response.meta.get('article_url', response.url)

        try:
            # Wait a bit for content to load
            await page.wait_for_timeout(2000)

            # Extract title - multiple methods
            title = "No title"

            # Method 1: Try the specific h4 with data-test attribute
            title_elem = await page.query_selector('h4[data-test="htmlTag article_title"]')
            if title_elem:
                title = await title_elem.inner_text()
            else:
                # Method 2: Try the h4 inside the article container
                title_elem = await page.query_selector('article h4, div[data-schema-path="article"] h4')
                if title_elem:
                    title = await title_elem.inner_text()
                else:
                    # Method 3: Try any h1 (often used for titles)
                    title_elem = await page.query_selector('h1')
                    if title_elem:
                        title = await title_elem.inner_text()
                    else:
                        # Method 4: Try the page title
                        title = await page.title()
                        # Clean up title (remove site name if present)
                        if ' — ' in title:
                            title = title.split(' — ')[0]

            title = title.strip()
            self.logger.info(f"Processing article: {title[:60]}...")

            # Rest of your code remains the same...
            # Extract article text
            article_text_div = await page.query_selector(
                'div[data-test="htmlTag article_text"][data-schema-path="article.text"]')

            if article_text_div:
                paragraphs = await article_text_div.query_selector_all("p")
                full_text = []
                for p in paragraphs:
                    text = await p.inner_text()
                    if text.strip():
                        full_text.append(text.strip())

                full_text = '\n\n'.join(full_text)
            else:
                # Fallback: try to get all paragraphs
                all_paragraphs = await page.query_selector_all('p')
                full_text = []
                for p in all_paragraphs[:20]:  # Limit to first 20 paragraphs
                    text = await p.inner_text()
                    if text.strip() and len(text.strip()) > 20:  # Filter out short paragraphs
                        full_text.append(text.strip())

                full_text = '\n\n'.join(full_text)

            if not full_text:
                self.logger.warning(f"No article text found for {article_url}")
                return

            # Extract date from text
            date_str = self.extract_date(full_text)
            post_date = self.parse_date(date_str) if date_str else None

            # Check if article is within lookback period
            if post_date:
                days_old = (self.today - post_date).days
                self.logger.info(f"Article date: {post_date.strftime('%d.%m.%Y')} ({days_old} days old)")

                if days_old >= self.lookback_days:
                    self.logger.info(f"Skipping article - too old ({days_old} days)")
                    return
            else:
                self.logger.warning("Could not parse article date")

            # Create item
            item = {
                'title': title,
                'full_text': full_text,
                'post_date': post_date.isoformat() if post_date else None,
                'url': article_url.rstrip('/'),
                'source': 'tbank.ru',
                'scraped_at': datetime.now().isoformat(),
                'date_parsed': date_str if date_str else None
            }

            yield item

        except Exception as e:
            self.logger.error(f"Error parsing article {article_url}: {e}")
        finally:
            # Always close the page
            await page.close()

    async def close_page_on_error(self, failure):
        """Close page if there's an error"""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.request.url} - {str(failure.value)}")

    def extract_date(self, text):
        """Extract date string from text using patterns"""
        date_patterns = [
            r'(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})',
            r'(\d{2}\.\d{2}\.\d{4})',  # DD.MM.YYYY
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def parse_date(self, date_string):
        """Parse date string to datetime object"""
        try:
            # Handle Russian date format: "27 декабря 2025"
            date_string = date_string.replace(' г.', '').strip()
            match = re.search(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})', date_string.lower())
            if match:
                day = int(match.group(1))
                month_ru = match.group(2)
                year = int(match.group(3))

                if month_ru in self.RU_MONTHS:
                    return datetime(year, self.RU_MONTHS[month_ru], day)

            # Try DD.MM.YYYY format
            match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_string)
            if match:
                day, month, year = map(int, match.groups())
                return datetime(year, month, day)

            # Try YYYY-MM-DD format
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_string)
            if match:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day)

        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_string}': {e}")

        return None
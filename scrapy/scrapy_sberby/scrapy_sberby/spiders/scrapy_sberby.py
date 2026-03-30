import scrapy
from urllib.parse import urljoin
from datetime import datetime

class Scrapy_SberbySpider(scrapy.Spider):
    name = 'scrapy_sberby'
    allowed_domains = ['www.sber-bank.by']

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
        },
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 30000,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    def __init__(self, *args, **kwargs):
        super(Scrapy_SberbySpider, self).__init__(*args, **kwargs)

        # Configuration
        self.max_pages = 100  # Maximum pages to crawl
        self.articles_saved = 0

        self.logger.info(f"Maximum pages to crawl: {self.max_pages}")

    def start_requests(self):
        """Start crawling from the base URL with Playwright"""
        start_url = "https://www.sber-bank.by/page/articles"
        self.logger.info(f"Starting URL: {start_url}")
        yield scrapy.Request(
            url=start_url,
            callback=self.parse_homepage,
            meta={
                'page': 1,
                'playwright': True,
                'playwright_include_page': True,
                'playwright_page_goto_kwargs': {'wait_until': 'networkidle', 'timeout': 30000}
            }
        )

    def parse_homepage(self, response):
        """Parse the homepage and extract article links"""
        page = response.meta['page']

        # Close the Playwright page to free resources
        if 'playwright_page' in response.meta:
            page_obj = response.meta['playwright_page']
            page_obj.close()

        self.logger.info(f"Parsing page {page}")

        # Extract article links using the correct selector
        article_links = response.css('a.styles_card__3LKGA::attr(href)').getall()

        self.logger.info(f"Found {len(article_links)} articles on page {page}")

        # Process article links
        for article_idx, href in enumerate(article_links[:50], start=1):  # Limit to 50 per page
            if not href:
                continue

            # Build full URL
            article_url = urljoin('https://www.sber-bank.by', href)

            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={
                    'page': page,
                    'article_idx': article_idx,
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_goto_kwargs': {'wait_until': 'networkidle', 'timeout': 30000}
                }
            )

        # Pagination - check if we should continue to next page
        if page < self.max_pages:
            next_page_selector = 'a[rel="next"]::attr(href)'
            next_page = response.css(next_page_selector).get()

            if next_page:
                next_url = urljoin('https://www.sber-bank.by/page/articles', next_page)
                self.logger.info(f"Loading next page: {next_url}")

                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_homepage,
                    meta={
                        'page': page + 1,
                        'playwright': True,
                        'playwright_include_page': True,
                        'playwright_page_goto_kwargs': {'wait_until': 'networkidle', 'timeout': 30000}
                    }
                )

    def parse_article(self, response):
        """Parse individual article and extract details"""
        page = response.meta.get('page', 0)
        article_idx = response.meta.get('article_idx', 0)

        # Close the Playwright page
        if 'playwright_page' in response.meta:
            page_obj = response.meta['playwright_page']
            page_obj.close()

        # Extract title using the correct selector for article pages
        title = response.css('div.BPSsiteUsefulArticleContent__article-title::text').get()
        if not title:
            # Fallback: try to extract from meta title tag
            meta_title = response.css('title::text').get()
            if meta_title:
                # Extract title from meta format: "ОАО «Сбер Банк» - Полезная статья  - ARTICLE TITLE"
                parts = [p.strip() for p in meta_title.split('-')]
                if len(parts) >= 3:
                    title = '-'.join(parts[2:]).strip()
                else:
                    title = parts[-1].strip()

        if title:
            title = title.strip()
        else:
            self.logger.warning(f"No title found for {response.url}, skipping")
            return

        # Extract article content using the correct selector
        content = response.css('div.BPSsiteUsefulArticleContent__article-content ::text').getall()
        if content:
            full_text = ' '.join(content).strip()
        else:
            # Fallback: try to extract content from other selectors
            content = response.css('article ::text, div[class*="content"] ::text, div[class*="Content"] ::text').getall()
            if content:
                full_text = ' '.join(content).strip()
            else:
                self.logger.warning(f"No content found for {response.url}, skipping")
                return

        # Clean up content - remove extra whitespace
        full_text = ' '.join(full_text.split())

        # Get current timestamp
        scraped_at = datetime.now().isoformat()

        # Use URL as primary key (no post_date field)
        url = response.url.rstrip('/')

        self.articles_saved += 1
        self.logger.info(f"✓ Article [{page}][{article_idx}]: {title[:60]}...")

        yield {
            'title': title,
            'url': url,  # URL is the primary key
            'content': full_text,
            'scraped_at': scraped_at,
        }

    def closed(self, reason):
        """Called when spider is closed"""
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed. Total articles saved: {self.articles_saved}")
        self.logger.info(f"Reason: {reason}")
        self.logger.info("=" * 60)

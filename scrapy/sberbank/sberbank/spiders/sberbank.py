import scrapy
import time
from scrapy_playwright.page import PageMethod
from urllib.parse import urljoin
from datetime import datetime


class SberbankPlaywrightSpider(scrapy.Spider):
    name = "sber"
    allowed_domains = ["sberbank.ru"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_TIMEOUT": 60,
        "DOWNLOAD_DELAY": 2,  # Increased to avoid rate limiting
        "CONCURRENT_REQUESTS": 1,  # Reduced to 1 to avoid blocking
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        },
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
    }

    def __init__(self, *args, **kwargs):
        super(SberbankPlaywrightSpider, self).__init__(*args, **kwargs)

        # Configuration
        self.max_pages = 100  # Maximum pages to crawl
        self.articles_saved = 0  # Track total articles saved

        self.logger.info(f"Maximum pages to crawl: {self.max_pages}")

    def start_requests(self):
        """Start crawling from page 1 with Playwright"""
        start_url = "https://www.sberbank.ru/ru/sberpress/all"
        self.logger.info(f"Starting URL: {start_url}")

        # Realistic Chrome User-Agent for Linux
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # JavaScript to hide automation indicators
        hide_automation_script = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
        """

        yield scrapy.Request(
            url=start_url,
            callback=self.parse_news_list,
            headers={"User-Agent": user_agent},
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_goto_kwargs": {
                    "wait_until": "domcontentloaded",
                    "timeout": 120000,  # 120 seconds - give more time for challenge
                },
                "playwright_context_kwargs": {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080},
                    "locale": "ru-RU",
                    "timezone_id": "Europe/Moscow",
                },
                "page": 1,
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 10000),  # Wait 10s for initial challenge
                    PageMethod("evaluate", hide_automation_script),
                    PageMethod("wait_for_selector", "body", timeout=60000),  # Wait for body to be populated
                    PageMethod("wait_for_timeout", 5000),  # Additional wait for content
                ],
            },
            errback=self.errback_httpbin,
        )

    def parse_news_list(self, response):
        """Parse the news list page and extract article links"""
        page = response.meta["page"]

        # Check if Playwright was used
        is_playwright = response.meta.get("playwright", False)
        self.logger.info(f"Parsing page {page} (playwright={is_playwright})")

        # Debug: log page length and check for key elements
        self.logger.info(f"Response body length: {len(response.text)} characters")

        # Check if we're still on the JavaScript challenge page
        if "TSPD" in response.text and "Please enable JavaScript" in response.text:
            self.logger.error("JS CHALLENGE FAILED: Still on the TSPD challenge page. JavaScript challenge not completed.")
            self.logger.info(f"Body content preview: {response.text[:500]}")
            return

        # Check if we're being blocked by WAF
        if "Возникла проблема при открытии сайта" in response.text or "user_blocked" in response.text:
            self.logger.error("WAF BLOCKED: Sberbank is blocking the request. Spider will not work with current configuration.")
            return

        # Check if news-archive-list exists
        news_list_exists = response.css("div.news-archive-list").get()
        self.logger.info(f"News archive list exists: {news_list_exists is not None}")

        # Debug: if no content found, show HTML structure
        if not news_list_exists and len(response.text) < 20000:
            self.logger.info(f"=== DEBUG: HTML Response (first 2000 chars) ===")
            self.logger.info(response.text[:2000])
            self.logger.info(f"=== END DEBUG ===")

        # Check if title links exist
        title_links_before = response.css("a.news-archive-list__title").getall()
        self.logger.info(f"Title links found before wait: {len(title_links_before)}")

        # Wait for articles to load if using Playwright
        if is_playwright:
            response.css("a.news-archive-list__title").getall()
            time.sleep(5)
            title_links = response.css("a.news-archive-list__title").getall()
            self.logger.info(f"Waiting for article links to load...")

        # Find all article title links
        article_links = response.css("a.news-archive-list__title")

        self.logger.info(f"Found {len(article_links)} articles on page {page}")

        # Track article index on this page
        for article_idx, link_elem in enumerate(article_links, start=1):
            # Extract title from the div inside the link
            title = link_elem.css(
                "div.dk-sbol-text.dk-sbol-text_size_body1::text"
            ).get()

            if not title:
                # Fallback: try to get any text from the link
                title = " ".join(link_elem.css("::text").getall()).strip()

            if not title:
                self.logger.warning(f"No title found for article #{article_idx}")
                continue

            title = title.strip()

            # Extract href from the link element
            href = link_elem.css("::attr(href)").get()

            if not href:
                self.logger.warning(f"No link found for article: {title[:60]}")
                continue

            # Build full URL
            article_url = urljoin("https://www.sberbank.ru", href)

            # Use current datetime as post_date (since all show "Сегодня")
            post_date = datetime.now()

            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                headers={"User-Agent": user_agent},
                meta={
                    "playwright": True,  # Enable Playwright for article pages too
                    "page": page,
                    "article_idx": article_idx,
                    "title": title,
                    "post_date": post_date,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                    "playwright_context_kwargs": {
                        "user_agent": user_agent,
                        "viewport": {"width": 1920, "height": 1080},
                    },
                },
                errback=self.errback_httpbin,
            )

        # Pagination - check if we should continue to next page
        if page < self.max_pages:
            next_page_num = page + 1

            # Check if there's a next page link in the page
            next_page_link = response.css("a.pagination__link.next::attr(href)").get()

            if next_page_link:
                next_url = urljoin("https://www.sberbank.ru", next_page_link)
                self.logger.info(f"Loading next page: {next_url}")

                user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_news_list,
                    headers={"User-Agent": user_agent},
                    meta={
                        "playwright": True,
                        "page": next_page_num,
                        "playwright_page_goto_kwargs": {
                            "wait_until": "networkidle",
                            "timeout": 90000,
                        },
                        "playwright_context_kwargs": {
                            "user_agent": user_agent,
                            "viewport": {"width": 1920, "height": 1080},
                        },
                    },
                    errback=self.errback_httpbin,
                )
            else:
                self.logger.info(f"No more pages found after page {page}")
        else:
            self.logger.info(f"Reached maximum page limit ({self.max_pages})")

    def parse_article(self, response):
        """Parse individual article and extract details"""
        # Get page, article index, title, and post_date from meta
        page = response.meta.get("page", 0)
        article_idx = response.meta.get("article_idx", 0)
        title = response.meta.get("title", "")
        post_date = response.meta.get("post_date", datetime.now())

        if not title:
            self.logger.warning(f"No title in meta for {response.url}, skipping")
            return

        # Extract article content - try multiple possible selectors
        # The article should contain paragraphs, headings, etc.
        article_body = response.css(
            "div.news-detail__content, div.article__body, div.page-news__content, div.page-content"
        )

        if not article_body:
            # Try to find any main content div
            article_body = response.css("main, article, [role='main']")

        if article_body:
            # Extract all paragraphs and headings, skip images
            text_parts = []

            # Get all paragraphs
            for p in article_body.css("p"):
                # Skip paragraphs that only contain images or are empty
                p_text = " ".join(p.css("::text").getall()).strip()
                if p_text and not p.css("img"):
                    text_parts.append(p_text)

            # Get all headings (h1, h2, h3, etc.)
            for h in article_body.css("h1, h2, h3, h4, h5, h6"):
                h_text = " ".join(h.css("::text").getall()).strip()
                if h_text:
                    text_parts.append(h_text)

            # Join all text parts
            full_text = "\n\n".join(text_parts).strip()

            if not full_text:
                # Fallback: get all text from article body
                full_text = " ".join(article_body.css("::text").getall()).strip()
        else:
            self.logger.warning(f"No article body found for {response.url}, skipping")
            return

        if not full_text:
            self.logger.warning(
                f"No text content extracted for {response.url}, skipping"
            )
            return

        # Get current timestamp for scraped_at
        scraped_at = datetime.now().isoformat()

        self.articles_saved += 1
        date_str = post_date.strftime("%d.%m.%Y") if post_date else "Unknown"
        self.logger.info(
            f"✓ Article [{page}][{article_idx}]: {title[:60]}... ({date_str})"
        )

        yield {
            "page": page,
            "article_idx": article_idx,
            "title": title,
            "full_text": full_text,
            "post_date": post_date.isoformat(),
            "scraped_at": scraped_at,
            "url": response.url.rstrip("/"),
            "processed": False,
        }

    def errback_httpbin(self, failure):
        self.logger.error(repr(failure))
        return failure.request

    def closed(self, reason):
        """Called when spider is closed"""
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed. Total articles saved: {self.articles_saved}")
        self.logger.info(f"Reason: {reason}")
        self.logger.info("=" * 60)

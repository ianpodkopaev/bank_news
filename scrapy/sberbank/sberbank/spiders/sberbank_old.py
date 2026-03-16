import scrapy
from urllib.parse import urljoin
from datetime import datetime


class SberbankSpider(scrapy.Spider):
    name = "sber"
    allowed_domains = ["sberbank.ru"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_TIMEOUT": 30,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 16,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    def __init__(self, *args, **kwargs):
        super(SberbankSpider, self).__init__(*args, **kwargs)

        # Configuration
        self.max_pages = 100  # Maximum pages to crawl
        self.articles_saved = 0  # Track total articles saved

        self.logger.info(f"Maximum pages to crawl: {self.max_pages}")

    def start_requests(self):
        """Start crawling from page 1"""
        start_url = "https://www.sberbank.ru/ru/sberpress/all"
        self.logger.info(f"Starting URL: {start_url}")
        yield scrapy.Request(
            url=start_url, callback=self.parse_news_list, meta={"page": 1}
        )

    def parse_news_list(self, response):
        """Parse the news list page and extract article links"""
        page = response.meta["page"]

        self.logger.info(f"Parsing page {page}")

        # Debug: Save response body to file for inspection
        with open("/tmp/sberbank_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        self.logger.info(f"Response body length: {len(response.text)} characters")

        # Find all article title links
        article_links = response.css("a.news-archive-list__title")

        self.logger.info(f"Found {len(article_links)} articles on page {page}")

        # Debug: Check if any links exist with 'news-archive-list' class
        all_links = response.css("a[href*='sberpress/all/article']")
        self.logger.info(f"Total links with 'sberpress/all/article': {len(all_links)}")

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

            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={
                    "page": page,
                    "article_idx": article_idx,
                    "title": title,
                    "post_date": post_date,
                },
            )

        # Pagination - check if we should continue to next page
        if page < self.max_pages:
            next_page_num = page + 1

            # Check if there's a next page link in the page
            next_page_link = response.css("a.pagination__link.next::attr(href)").get()

            if next_page_link:
                next_url = urljoin("https://www.sberbank.ru", next_page_link)
                self.logger.info(f"Loading next page: {next_url}")

                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_news_list,
                    meta={"page": next_page_num},
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
        article_body = response.css("div.news-detail__content, div.article__body, div.page-news__content, div.page-content")

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
            self.logger.warning(f"No text content extracted for {response.url}, skipping")
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

    def closed(self, reason):
        """Called when spider is closed"""
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed. Total articles saved: {self.articles_saved}")
        self.logger.info(f"Reason: {reason}")
        self.logger.info("=" * 60)

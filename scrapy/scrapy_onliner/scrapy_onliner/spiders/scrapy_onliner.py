import scrapy
from urllib.parse import urljoin
from datetime import datetime, timedelta
import re

class Scrapy_OnlinerSpider(scrapy.Spider):
    name = 'onliner'
    allowed_domains = ['money.onliner.by']

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    def __init__(self, *args, **kwargs):
        super(Scrapy_OnlinerSpider, self).__init__(*args, **kwargs)

        # Configuration
        self.lookback_days = 7  # Stop when articles are older than this
        self.max_pages = 100  # Maximum pages to crawl
        self.articles_saved = 0
        self.today = datetime.now()

        self.logger.info(f"Lookback period: {self.lookback_days} days")
        self.logger.info(f"Maximum pages to crawl: {self.max_pages}")

    def start_requests(self):
        """Start crawling from the base URL"""
        start_url = "https://money.onliner.by/tag/banki"
        self.logger.info(f"Starting URL: {start_url}")
        yield scrapy.Request(
            url=start_url,
            callback=self.parse_homepage,
            meta={'page': 1}
        )

    def parse_homepage(self, response):
        """Parse the homepage and extract article links"""
        page = response.meta['page']

        self.logger.info(f"Parsing page {page}")

        # Extract article links from within the news list container only
        # This limits extraction to the specific article items, not the entire wrapper
        news_list = response.css('div.news-tidings__list')
        article_links = news_list.css('a.news-tidings__stub::attr(href)').getall()
        article_links.extend(news_list.css('a.news-tiles__stub::attr(href)').getall())

        self.logger.info(f"Found {len(article_links)} articles on page {page}")

        # Process article links
        for article_idx, href in enumerate(article_links[:50], start=1):  # Limit to 50 per page
            if not href:
                continue

            # Build full URL
            article_url = urljoin('https://money.onliner.by', href)

            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={
                    'page': page,
                    'article_idx': article_idx
                }
            )

        # Pagination - check if we should continue to next page
        if page < self.max_pages:
            next_page_selector = 'a[rel="next"]::attr(href)'
            next_page = response.css(next_page_selector).get()

            if next_page:
                next_url = urljoin('https://money.onliner.by', next_page)
                self.logger.info(f"Loading next page: {next_url}")

                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_homepage,
                    meta={'page': page + 1}
                )

    def parse_article(self, response):
        """Parse individual article and extract details"""
        page = response.meta.get('page', 0)
        article_idx = response.meta.get('article_idx', 0)

        # Extract title using provided selector
        title = response.css('h1::text').get()
        if title:
            title = title.strip()
        else:
            self.logger.warning(f"No title found for {response.url}, skipping")
            return

        # Extract publication date
        date_text = response.css('div.news-header__time::text').get()
        if date_text:
            post_date = self.parse_date(date_text.strip())
        else:
            self.logger.warning(f"No date found for {response.url}")
            post_date = None

        # Check if article is too old
        if post_date:
            days_old = (self.today - post_date).days
            if days_old >= self.lookback_days:
                self.logger.info(f"Article is {days_old} days old (>= {self.lookback_days} days lookback)")
                return

        # Extract article content using provided selector
        content_paragraphs = response.css('div.news-text p::text').getall()
        if content_paragraphs:
            # Join all paragraph texts with proper spacing
            full_text = '\n\n'.join([p.strip() for p in content_paragraphs if p.strip()]).strip()
        else:
            self.logger.warning(f"No content found for {response.url}, skipping")
            return

        # Get current timestamp
        scraped_at = datetime.now().isoformat()

        self.articles_saved += 1
        date_str = post_date.strftime('%d.%m.%Y') if post_date else 'Unknown'
        self.logger.info(f"✓ Article [{page}][{article_idx}]: {title[:60]}... ({date_str})")

        yield {
            'title': title,
            'url': response.url.rstrip('/'),
            'content': full_text,
            'post_date': post_date.isoformat() if post_date else None,
            'scraped_at': scraped_at,
            'source': "onliner", 
        }

    def parse_date(self, date_string):
        """Parse various date formats including Russian dates"""
        if not date_string:
            return None

        date_string = date_string.strip()

        # Russian month names
        ru_months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }

        try:
            # Russian date format: "08 января 2026, 19:51" or "08 января 2026"
            match = re.search(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})(?:,\s+(\d{1,2}):(\d{2}))?', date_string.lower())
            if match:
                day = int(match.group(1))
                month_ru = match.group(2)
                year = int(match.group(3))

                # Time is optional
                if match.group(4) and match.group(5):
                    hour = int(match.group(4))
                    minute = int(match.group(5))
                    if month_ru in ru_months:
                        return datetime(year, ru_months[month_ru], day, hour, minute)
                else:
                    if month_ru in ru_months:
                        return datetime(year, ru_months[month_ru], day)

            # DD.MM.YYYY format
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_string):
                return datetime.strptime(date_string, '%d.%m.%Y')

            # ISO format: "2025-12-27" or "2025-12-27T10:30:00"
            if '-' in date_string and date_string[4] == '-':
                try:
                    date_part = date_string.split('T')[0]
                    return datetime.strptime(date_part, '%Y-%m-%d')
                except ValueError:
                    pass

            # MM/DD/YYYY format
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_string):
                return datetime.strptime(date_string, '%m/%d/%Y')

        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_string}': {e}")

        return None

    def closed(self, reason):
        """Called when spider is closed"""
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed. Total articles saved: {self.articles_saved}")
        self.logger.info(f"Reason: {reason}")
        self.logger.info("=" * 60)

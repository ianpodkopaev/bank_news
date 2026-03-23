import scrapy
from scrapy_officelife.items import ScrapyOfficelifeItem
from datetime import datetime, timedelta
import re
import urllib.parse


class OfficelifeSpider(scrapy.Spider):
    name = "officelife"
    allowed_domains = ["officelife.media"]
    start_urls = ["https://officelife.media/tags/banks/"]

    # Maximum pages to crawl
    max_pages = 100
    current_page = 1

    # Only crawl articles from last N days
    lookback_days = 7
    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 1,
    }

    def parse(self, response):
        """Parse the listing page and extract article links and dates"""
        self.logger.info(f"Parsing page {self.current_page}: {response.url}")

        # Extract news items with their dates
        news_items = response.css('.news-section__item')

        self.logger.info(f"Found {len(news_items)} articles on page {self.current_page}")

        for item in news_items:
            # Extract article link
            link = item.css('a.news__content::attr(href)').get()
            if not link:
                continue

            # Extract date from main page
            date_text = item.css('span.news__date::text').get()
            parsed_date = self.parse_date(date_text)

            if not parsed_date:
                self.logger.warning(f"Could not parse date: {date_text}")
                continue

            # Check if article is within lookback period
            if parsed_date < self.cutoff_date:
                self.logger.info(f"Article too old: {parsed_date} (cutoff: {self.cutoff_date})")
                continue

            # Make URL absolute
            absolute_url = response.urljoin(link)
            self.logger.debug(f"Scheduling article: {absolute_url}")

            # Schedule the article page for scraping, passing the date
            yield scrapy.Request(
                url=absolute_url,
                callback=self.parse_article,
                meta={'url': absolute_url, 'date': parsed_date}
            )

        # Find and follow pagination link if it exists
        # Look for next page link - common patterns
        next_page_selectors = [
            'a[rel="next"]::attr(href)',
            '.pagination-next::attr(href)',
            'a.pagination__item--next::attr(href)',
            '.pagination a:not(.active)::attr(href)',
        ]

        next_page = None
        for selector in next_page_selectors:
            next_page = response.css(selector).get()
            if next_page:
                break

        if next_page and self.current_page < self.max_pages:
            self.current_page += 1
            absolute_next_page = response.urljoin(next_page)
            self.logger.info(f"Following next page: {absolute_next_page}")
            yield scrapy.Request(url=absolute_next_page, callback=self.parse)
        else:
            self.logger.info("No more pages or max pages reached")

    def parse_article(self, response):
        """Parse individual article page"""
        url = response.meta.get('url', response.url)
        parsed_date = response.meta.get('date')

        self.logger.info(f"Parsing article: {url}")

        try:
            # Extract title from h1 or page header
            title_selectors = [
                'h1.page-header-section__title::text',
                'h1::text',
                '.article-title::text',
            ]

            title = None
            for selector in title_selectors:
                title = response.css(selector).get()
                if title:
                    break

            # Extract content from article body
            content_selectors = [
                'div[itemprop="articleBody"] ::text',
                'div.article-content ::text',
                '.article-body ::text',
                'div.content ::text',
            ]

            content_parts = []
            for selector in content_selectors:
                content_parts = response.css(selector).getall()
                if content_parts:
                    break

            # Clean and join content
            content = ' '.join([text.strip() for text in content_parts if text.strip()])

            # Create item (date already parsed from main page)
            item = ScrapyOfficelifeItem(
                title=title.strip() if title else '',
                full_text=content.strip(),
                post_date=parsed_date.isoformat() if parsed_date else datetime.now().isoformat(),
                url=url.rstrip('/'),
                source='officelife',
                scraped_at=datetime.now().isoformat()
            )

            self.logger.info(f"Successfully scraped: {title}")
            yield item

        except Exception as e:
            self.logger.error(f"Error parsing article {url}: {str(e)}")

    def parse_date(self, date_string):
        """Parse date from various Russian date formats"""
        if not date_string:
            return None

        date_string = date_string.strip()

        # Russian month names
        months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }

        # Try various date formats

        # Format: "20 марта в 9:00" or "20 марта 2025 в 9:00"
        match = re.match(r'(\d{1,2})\s+([а-я]+)\s*(\d{4})?\s*(?:в)?\s*(\d{1,2}):(\d{2})', date_string)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3)) if match.group(3) else datetime.now().year
            hour = int(match.group(4))
            minute = int(match.group(5))

            if month_name.lower() in months:
                month = months[month_name.lower()]
                return datetime(year, month, day, hour, minute)

        # Format: "20.03.2026 09:00:00" (from data-time attribute)
        match = re.match(r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2}):(\d{2})', date_string)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            return datetime(year, month, day, hour, minute, second)

        # Format: "2025-03-20T09:00:00" (ISO format)
        try:
            return datetime.fromisoformat(date_string.replace('T', ' '))
        except ValueError:
            pass

        self.logger.warning(f"Could not parse date string: {date_string}")
        return None

import asyncio
import sys
import os
from datetime import datetime, timedelta
import re
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from playwright.async_api import async_playwright
from dotenv import load_dotenv


class TBankScraper:
    def __init__(self):
        load_dotenv()
        self.lookback_days = 30
        self.max_pages = 10
        self.articles_saved = 0
        self.today = datetime.now()

        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.mongo_username = os.getenv('MONGO_USERNAME')
        self.mongo_password = os.getenv('MONGO_PASSWORD')
        self.mongo_database = os.getenv('MONGO_DATABASE', 'crawlab')
        self.mongo_collection = os.getenv('MONGO_COLLECTION', 'results_news_telegram')

        self.client = None
        self.collection = None
        self.mongo_connected = False

        try:
            if self.mongo_username and self.mongo_password:
                self.client = MongoClient(
                    self.mongo_uri,
                    username=self.mongo_username,
                    password=self.mongo_password
                )
            else:
                self.client = MongoClient(self.mongo_uri)

            db = self.client[self.mongo_database]
            self.collection = db[self.mongo_collection]

            self.collection.create_index([('url', ASCENDING)], unique=True)
            self.collection.create_index([('processed', ASCENDING)])

            self.mongo_connected = True
            print(f"Connected to MongoDB")

        except PyMongoError as e:
            print(f"Failed to connect to MongoDB: {e}")
        except Exception as e:
            print(f"Unexpected error connecting to MongoDB: {e}")

    def close(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

    def extract_date(self, text):
        date_patterns = [
            r'(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def parse_date(self, date_string):
        ru_months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }

        try:
            date_string = date_string.replace(' г.', '').strip()
            match = re.search(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})', date_string.lower())
            if match:
                day = int(match.group(1))
                month_ru = match.group(2)
                year = int(match.group(3))

                if month_ru in ru_months:
                    return datetime(year, ru_months[month_ru], day)
        except Exception as e:
            print(f"Failed to parse date '{date_string}': {e}")

        return None


async def main():
    print("T-Bank News Scraper")
    print("=" * 60)

    scraper = TBankScraper()
    print(f"Lookback period: {scraper.lookback_days} days")
    print(f"Maximum pages: {scraper.max_pages}")
    print(f"Target: https://www.tbank.ru/about/news/")
    print()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
            )
            page = await context.new_page()

            url = "https://www.tbank.ru/about/news/"
            print(f"\nLoading page: {url}")

            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            await asyncio.sleep(30)

            print("Searching for article links...")

            # Method 1: Try copy link elements first
            copy_links = await page.query_selector_all('[data-test="article_copyLink"]')
            print(f"Found {len(copy_links)} copy link elements")

            # Method 2: Also try anchor tags as fallback
            anchor_links = await page.query_selector_all('a[href*="/about/news/"]')
            print(f"Found {len(anchor_links)} anchor links")

            # Combine both
            all_article_links = []

            # Extract URLs from copy link elements
            for link_elem in copy_links:
                text = await link_elem.inner_text()
                if text and 'tbank.ru/about/news/' in text:
                    # Create a fake link element wrapper
                    all_article_links.append({'type': 'copy_link', 'url': text})

            # Extract URLs from anchor tags
            for link_elem in anchor_links:
                href = await link_elem.get_attribute('href')
                if href and href != '/about/news/' and href != 'https://www.tbank.ru/about/news/':
                    all_article_links.append({'type': 'anchor', 'element': link_elem})

            print(f"Total potential article links: {len(all_article_links)}")

            if not all_article_links:
                print("No article links found on page")
                await browser.close()
                scraper.close()
                sys.exit(0)

            articles_count = 0
            seen_urls = set()

            for idx, link_item in enumerate(all_article_links, start=1):
                try:
                    # Handle different link types
                    if link_item['type'] == 'copy_link':
                        article_url = link_item['url']
                        if not article_url.startswith('http'):
                            article_url = f"https://{article_url}"
                    else:
                        # anchor link
                        link_elem = link_item['element']
                        href = await link_elem.get_attribute('href')
                        if not href:
                            continue
                        article_url = href
                        if not article_url.startswith('http'):
                            article_url = f"https://www.tbank.ru{article_url}" if article_url.startswith('/') else article_url

                    if article_url in seen_urls:
                        print(f"Skipping duplicate URL: {article_url}")
                        continue

                    seen_urls.add(article_url)
                    print(f"[{idx}] {article_url}")

                    if scraper.mongo_connected:
                        existing = scraper.collection.find_one({'url': article_url})
                        if existing:
                            print(f"Skipping (already in database)")
                            articles_count += 1
                            continue

                    article_response = await page.goto(article_url, wait_until='domcontentloaded', timeout=30000)

                    await asyncio.sleep(2)

                    title_elem = await page.query_selector('h4[data-test="htmlTag article_title"]')
                    if title_elem:
                        title = await title_elem.inner_text()
                    else:
                        title_elem = await page.query_selector('h1, h2, h3')
                        title = await title_elem.inner_text() if title_elem else "No title"

                    if title:
                        title = title.strip()

                    print(f"Title: {title[:60]}")

                    article_text_div = await page.query_selector('div[data-test="htmlTag article_text"][data-schema-path="article.text"]')

                    if article_text_div:
                        paragraphs = await article_text_div.query_selector_all("p")
                        full_text = '\n\n'.join([await p.inner_text() for p in paragraphs if (await p.inner_text()).strip()])
                    else:
                        print(f"No article text div found")
                        articles_count += 1
                        continue

                    date_str = scraper.extract_date(full_text)
                    post_date = scraper.parse_date(date_str) if date_str else None

                    if post_date:
                        days_old = (scraper.today - post_date).days
                        if days_old >= scraper.lookback_days:
                            print(f"Article is {days_old} days old")
                            articles_count += 1
                            continue

                    scraped_at = datetime.now().isoformat()
                    article = {
                        'title': title,
                        'full_text': full_text,
                        'post_date': post_date.isoformat() if post_date else None,
                        'scraped_at': scraped_at,
                        'url': article_url.rstrip('/'),
                        'source': 'tbank.ru',
                        'processed': False,
                    }

                    if scraper.mongo_connected:
                        try:
                            result = scraper.collection.insert_one(article)
                            scraper.articles_saved += 1
                            date_str_display = post_date.strftime('%d.%m.%Y') if post_date else 'Unknown'
                            print(f"Saved: {title[:50]}... ({date_str_display})")
                            articles_count += 1
                        except PyMongoError as e:
                            print(f"Error saving to MongoDB: {e}")

                except Exception as e:
                    print(f"Error processing article [{idx}]: {e}")
                    continue

            await browser.close()

            print("\n" + "=" * 60)
            print(f"Scraping completed!")
            print(f"Total articles processed: {len(all_article_links)}")
            print(f"Articles saved to MongoDB: {scraper.articles_saved}")
            print("=" * 60)

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\nError during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())

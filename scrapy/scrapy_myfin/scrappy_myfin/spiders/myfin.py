import scrapy
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime, timedelta

class MyfinSpider(scrapy.Spider):
    name = "myfin"
    allowed_domains = ["myfin.by"]
    start_urls = ["https://myfin.by"]

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    # Категории и ключевые слова для классификации (same as bankcnews)
    CATEGORIES = {
        'potential_effect': {
            'Экономия ресурсов': [
                'экономия времени', 'сокращение затрат', 'оптимизация FTE', 'высвобождение ресурсов',
                'снижение трудоемкости', 'time savings', 'cost reduction', 'FTE optimization',
                'resource release', 'labor reduction', 'автоматизация', 'оптимизация'
            ],
            'Повышение качества': [
                'улучшение пользовательского опыта', 'повышение точности данных', 'снижение ошибок',
                'увеличение скорости отклика', 'улучшение надежности', 'accuracy improvement',
                'reliability enhancement', 'satisfaction increase', 'speed boost', 'UX improvement',
                'error rate reduction', 'response time improvement', 'качество', 'точность'
            ],
            'Снижение рисков': [
                'безопасность', 'комплаенс', 'контроль', 'требованиям', 'предотвращение потерь',
                'улучшение контроля', 'снижение операционных рисков', 'минимизация сбоев',
                'Regulatory compliance', 'loss prevention', 'control enhancement',
                'operational risk reduction', 'failure minimization', 'фрод', 'мошенничество', 'AML'
            ],
            'Новые возможности': [
                'доход', 'монетизация', 'новая функция', 'innovation', 'product development',
                'competitive positioning', 'revenue diversification', 'partnership development',
                'новый продукт', 'развитие', 'инновация'
            ]
        },
        'complexity': {
            'Низкая': [
                'настройка', 'шаблон', 'готовое решение', 'low-code', 'no-code', 'подключение',
                'активация', 'базовая конфигурация', 'configuration', 'template', 'ready-made solution',
                'connection', 'activation', 'basic setup'
            ],
            'Средняя': [
                'доработка', 'интеграция', 'микросервис', 'конфигурация', 'адаптация', 'модификация',
                'промежуточное решение', 'customization', 'integration', 'API', 'microservice',
                'adaptation', 'modification'
            ],
            'Высокая': [
                'разработка', 'внедрение', 'кастомизация', 'миграция', 'обучение модели', 'платформа',
                'замена системы', 'R&D', 'лицензия', 'оборудование', 'development', 'implementation',
                'customization', 'migration', 'обучение ИИ'
            ]
        },
        'relevance': {
            'Раннее внедрение': [
                'первые внедрения', 'ограниченное использование', 'начальное применение',
                'тестовые проекты', 'апробация', 'валидация', 'рассматривают возможность внедрения',
                'запустили', 'внедряют', 'используют', 'first implementations', 'limited deployment',
                'test projects', 'growing interest', 'niche application', 'technology validation',
                'pilot implementation', 'пилот', 'тестирование'
            ],
            'Зрелый тренд': [
                'стандарт', 'лучшая практика', 'массово', 'регулятор требует', 'распространенное решение',
                'проверенная технология', 'industry standard', 'mass adoption', 'proven solutions',
                'best practices', 'established methodologies', 'widespread technology'
            ],
            'Концепт': [
                'исследование', 'может использоваться', 'перспективный', 'растет популярность',
                'эксперимент', 'тестирование', 'прототип', 'гипотеза', 'начальная стадия',
                'experimental stage', 'academic research', 'theoretical framework', 'initial phase',
                'R&D', 'lab testing', 'исследование'
            ]
        },
        'scope': {
            'Бэк-офис и Документооборот': [
                'документ', 'договор', 'ведение', 'обработка', 'заявка', 'KYC', 'документооборот',
                'back-office', 'обработка документов'
            ],
            'Финансы и Отчетность': [
                'отчет', 'ЦБ', 'МСФО', 'казначейство', 'ликвидность', 'проводка', 'финансы',
                'отчетность', 'бухгалтерия'
            ],
            'Риски и Комплаенс': [
                'фрод', 'мошенничество', 'AML', 'контроль', 'аудит', 'безопасность', 'риски',
                'комплаенс', 'регулятор'
            ],
            'ИТ и Инфраструктура': [
                'инфраструктура', 'API', 'интеграция', '1С', 'БКС', 'миграция', 'RPA', 'ИТ',
                'технологии', 'система'
            ]
        },
        'key_functions': {
            'Аналитика и Мониторинг': [
                'анализ в реальном времени', 'отслеживание', 'дашборд', 'отчет', 'KPI', 'аналитика',
                'мониторинг', 'отслеживание'
            ],
            'Автоматизация процессов': [
                'автоматизация', 'робот', 'RPA', 'сценарий', 'workflow', 'автоматизация процессов'
            ],
            'Взаимодействие и Коммуникация': [
                'уведомление', 'оповещение', 'чат', 'портал', 'имейл', 'коммуникация', 'взаимодействие'
            ],
            'Безопасность и Контроль': [
                'контроль доступа', 'верификация', 'мониторинг транзакций', 'алерт', 'безопасность',
                'контроль'
            ]
        }
    }

    # AI и технологии ключевые слова (same as bankcnews)
    AI_KEYWORDS = [
        'ai', 'artificial intelligence', 'machine learning', 'deep learning', 'нейросеть',
        'искусственный интеллект', 'машинное обучение', 'AI', 'ML', 'ИИ', 'нейронная сеть',
        'tensorflow', 'pytorch', 'scikit-learn', 'openai', 'chatgpt', 'бот', 'chatbot',
        'компьютерное зрение', 'nlp', 'обработка естественного языка'
    ]

    def __init__(self, *args, **kwargs):
        super(MyfinSpider, self).__init__(*args, **kwargs)
        # Calculate date threshold (today - 7 days)
        self.date_threshold = datetime.now() - timedelta(days=7)
        self.logger.info(f"Date threshold: {self.date_threshold.strftime('%d %B %Y')}")

    def start_requests(self):
        """Start with search terms for finance-related content"""
        search_terms = ['банк', 'финансы', 'кредит', 'банки', 'искусственный интеллект', 'AI', 'машинное обучение']

        for term in search_terms:
            # Try to access main site first and then look for search functionality
            yield scrapy.Request(
                url="https://myfin.by",
                callback=self.parse_main_page,
                meta={'search_term': term}
            )

    def parse_main_page(self, response):
        """Parse the main page and look for content or search links"""
        search_term = response.meta['search_term']
        self.logger.info(f"Parsing main page for content related to '{search_term}'")

        # Look for news articles, blog posts, or content sections
        article_links = []

        # Try to find article links with various selectors
        selectors = [
            'a[href*="/news/"]',
            'a[href*="/article/"]',
            'a[href*="/blog/"]',
            'a[href*="/publication/"]',
            '.news-item a',
            '.article-item a',
            '.content-item a',
            'a[class*="news"]',
            'a[class*="article"]'
        ]

        for selector in selectors:
            links = response.css(selector)
            for link in links:
                href = link.css('::attr(href)').get()
                if href:
                    clean_url = self.clean_url(href)
                    if clean_url and self.is_valid_article_url(clean_url):
                        article_links.append(clean_url)

        # Remove duplicates
        article_links = list(set(article_links))
        self.logger.info(f"Found {len(article_links)} potential article links")

        # Follow found article links (limit to avoid overwhelming)
        for article_url in article_links[:5]:
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={'search_term': search_term}
            )

        # If no specific articles found, try to find search functionality
        if not article_links:
            # Look for search form or search page
            search_links = response.css('a[href*="search"]::attr(href)').getall()
            for search_link in search_links:
                if search_link:
                    clean_search_url = self.clean_url(search_link)
                    if clean_search_url:
                        yield scrapy.Request(
                            url=clean_search_url,
                            callback=self.parse_search_page,
                            meta={'search_term': search_term}
                        )

        # If still nothing, extract content from main page itself
        if not article_links and not response.css('a[href*="search"]'):
            yield from self.extract_content_from_page(response, search_term)

    def parse_search_page(self, response):
        """Parse search results page"""
        search_term = response.meta['search_term']

        # Look for search results similar to the original spider
        article_links = []
        search_items = response.css('a[href*="/news/"], a[href*="/article/"], .search-result a, .result-item a')

        for link in search_items:
            href = link.css('::attr(href)').get()
            if href:
                clean_url = self.clean_url(href)
                if clean_url and self.is_valid_article_url(clean_url):
                    article_links.append(clean_url)

        # Remove duplicates
        article_links = list(set(article_links))

        # Follow article links
        for article_url in article_links[:10]:
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={'search_term': search_term}
            )

    def extract_content_from_page(self, response, search_term):
        """Extract content from the current page if it's relevant"""
        # Extract title
        title = (response.css('h1::text').get() or
                response.css('title::text').get() or "").strip()

        # Extract all paragraphs
        all_paragraphs = self.extract_all_paragraphs(response)
        full_content = " ".join(all_paragraphs)

        # Combine all text for analysis
        full_text = f"{title} {full_content}".lower()

        # Categorize content
        categories = self.categorize_content(full_text)
        ai_related = self.detect_ai_content(full_text)

        # Check if content is relevant to search terms
        if search_term.lower() in full_text.lower() or len(full_content) > 100:
            yield {
                'title': title,
                'url': response.url,
                'search_term': search_term,
                'description': self.extract_description(response),
                'content_full': full_content,
                'content_length': len(full_content),
                'paragraphs_count': len(all_paragraphs),
                'ai_related': ai_related,
                'categories': categories,
                'article_date': None,  # Extracted from page, not individual article
                'scraping_timestamp': datetime.now().isoformat(),
                'scraped_at': datetime.now().isoformat(),
            }

    def parse_article(self, response):
        """Parse individual article pages"""
        search_term = response.meta['search_term']

        # Extract title
        title = (response.css('h1::text').get() or
                response.css('.article-title::text').get() or
                response.css('title::text').get() or "").strip()

        # Clean title from site name
        if ' - myfin.by' in title.lower() or ' - MyFin' in title:
            title = re.split(r' - [Mm]y[Ff]in', title)[0].strip()

        # Extract article date from <time datetime="..."> format
        article_date = self.extract_article_date(response)

        # Check if article is within 7 days
        if article_date and article_date < self.date_threshold:
            self.logger.info(f"Skipping old article from {article_date}: {title}")
            return

        # Extract description and ALL <p> content
        description = self.extract_description(response)
        all_paragraphs = self.extract_all_paragraphs(response)
        full_content = " ".join(all_paragraphs)

        # Combine all text for analysis
        full_text = f"{title} {description} {full_content}".lower()

        # Categorize content
        categories = self.categorize_content(full_text)
        ai_related = self.detect_ai_content(full_text)

        yield {
            'title': title,
            'url': response.url,
            'search_term': search_term,
            'description': description,
            'content_full': full_content,
            'content_length': len(full_content),
            'paragraphs_count': len(all_paragraphs),
            'ai_related': ai_related,
            'categories': categories,
            'article_date': article_date.isoformat() if article_date else None,
            'scraping_timestamp': datetime.now().isoformat(),
            'scraped_at': datetime.now().isoformat(),
        }

    def clean_url(self, url):
        """Clean and normalize URL"""
        if not url:
            return None

        url = re.sub(r'%3Ca.*?href=%22', '', url)
        url = re.sub(r'%22.*%3E.*%3C/a%3E', '', url)
        url = re.sub(r'&amp;', '&', url)

        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin('https://myfin.by', url)
        elif not url.startswith('http'):
            url = urljoin('https://myfin.by', url)

        if '%3C' in url or '%22' in url:
            return None

        return url

    def is_valid_article_url(self, url):
        """Check if URL is a valid article URL for myfin.by"""
        if not url.startswith('https://myfin.by/'):
            return False

        # Accept various content URL patterns
        valid_patterns = ['/news/', '/article/', '/blog/', '/publication/', '/info/']
        return any(pattern in url for pattern in valid_patterns)

    def extract_description(self, response):
        """Extract article description"""
        meta_desc = response.css('meta[name="description"]::attr(content)').get()
        if meta_desc and len(meta_desc) > 20:
            return meta_desc.strip()

        og_desc = response.css('meta[property="og:description"]::attr(content)').get()
        if og_desc and len(og_desc) > 20:
            return og_desc.strip()

        return "Description not available"

    def extract_all_paragraphs(self, response):
        """Extract ALL <p> tags from the entire page"""
        all_paragraphs = []

        # Get all <p> tags from the entire page
        paragraphs = response.css('p')

        for p in paragraphs:
            # Extract text from the paragraph and all its children
            text = p.css('::text').getall()
            if text:
                # Join all text nodes and clean
                full_text = ' '.join(text).strip()
                if full_text:
                    # Filter out very short paragraphs and advertising
                    if (len(full_text) > 10 and
                        not self.is_advertising(full_text)):
                        all_paragraphs.append(full_text)

        return all_paragraphs

    def is_advertising(self, text):
        """Check if text is advertising or unwanted content"""
        advertising_indicators = [
            'реклама', 'advertisement', 'advert', 'спонсор', 'sponsor',
            'партнерский материал', 'partner content', 'коммерческий',
            'читайте также', 'recommended', 'популярное', 'popular',
            'подпишитесь', 'subscribe', 'социальные сети', 'social media',
            'copyright', 'копирайт', 'все права защищены'
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in advertising_indicators)

    def categorize_content(self, text):
        """Categorize content based on predefined categories"""
        categories = {}

        for category_type, subcategories in self.CATEGORIES.items():
            category_results = {}
            for subcategory, keywords in subcategories.items():
                score = 0
                for keyword in keywords:
                    # Count occurrences of each keyword
                    occurrences = text.count(keyword.lower())
                    score += occurrences
                if score > 0:
                    category_results[subcategory] = score

            if category_results:
                # Get top category by score
                top_category = max(category_results.items(), key=lambda x: x[1])
                categories[category_type] = {
                    'primary': top_category[0],
                    'all_matches': category_results,
                    'confidence_score': min(top_category[1] / 10, 1.0),  # Normalize to 0-1
                    'total_keywords_found': sum(category_results.values())
                }

        return categories

    def extract_article_date(self, response):
        """Extract article date from <time datetime="..."> format"""
        try:
            # Look for time element with datetime attribute
            time_element = response.css('time[datetime]')

            if time_element:
                datetime_attr = time_element.css('::attr(datetime)').get()
                if datetime_attr:
                    # Parse datetime like "2025-11-25 08:28"
                    return self.parse_datetime_format(datetime_attr)

                # Also try to get text content as fallback
                time_text = time_element.css('::text').get()
                if time_text:
                    return self.parse_myfin_date_text(time_text.strip())

            return None
        except Exception as e:
            self.logger.warning(f"Failed to extract article date: {e}")
            return None

    def parse_datetime_format(self, datetime_str):
        """Parse datetime string like '2025-11-25 08:28'"""
        try:
            # Format: YYYY-MM-DD HH:MM
            return datetime.strptime(datetime_str.strip(), '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                # Try ISO format: YYYY-MM-DDTHH:MM:SS
                return datetime.fromisoformat(datetime_str.strip().replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Could not parse datetime format: {datetime_str}")
                return None

    def parse_myfin_date_text(self, date_text):
        """Parse date text from myfin time element content"""
        if not date_text:
            return None

        # Format: "08:28 25.11.2025"
        try:
            pattern = r'(\d{1,2}):(\d{2})\s+(\d{1,2})\.(\d{1,2})\.(\d{4})'
            match = re.search(pattern, date_text)

            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                day = int(match.group(3))
                month = int(match.group(4))
                year = int(match.group(5))
                return datetime(year, month, day, hour, minute)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse myfin date '{date_text}': {e}")
            return None

    def detect_ai_content(self, text):
        """Detect AI-related content"""
        ai_matches = {}

        for keyword in self.AI_KEYWORDS:
            count = text.count(keyword.lower())
            if count > 0:
                ai_matches[keyword] = count

        return {
            'is_ai_related': len(ai_matches) > 0,
            'ai_keywords_found': ai_matches,
            'ai_keyword_count': len(ai_matches),
            'total_mentions': sum(ai_matches.values()),
            'ai_content_score': min(sum(ai_matches.values()) / 5, 1.0)  # Normalize to 0-1
        }

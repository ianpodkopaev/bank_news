import scrapy
from urllib.parse import urljoin
import re
from datetime import datetime, timedelta

class BankinformSpider(scrapy.Spider):
    name = 'bankinform'
    allowed_domains = ['bankinform.ru']

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'FEED_FORMAT': 'json',
        'FEED_URI': 'file:///app/data/bankinform_articles_%(time)s.json',
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
        super(BankinformSpider, self).__init__(*args, **kwargs)
        # Calculate date threshold (today - 7 days)
        self.date_threshold = datetime.now() - timedelta(days=7)
        self.logger.info(f"Date threshold: {self.date_threshold.strftime('%d %B %Y')}")

    def start_requests(self):
        start_url = "https://bankinform.ru/news/tag/2149"
        yield scrapy.Request(
            url=start_url,
            callback=self.parse_article_list,
            meta={'page': 1}
        )

    def parse_article_list(self, response):
        page = response.meta['page']

        self.logger.info(f"Parsing Bankinform.ru page {page}")

        # Extract article links with titles and dates
        articles_data = self.extract_articles_with_data(response)

        self.logger.info(f"Found {len(articles_data)} articles on page {page}")

        # Follow article links to get full content
        for article_data in articles_data:
            if article_data['date'] is None or article_data['date'] >= self.date_threshold:
                yield scrapy.Request(
                    url=article_data['url'],
                    callback=self.parse_article,
                    meta={
                        'title': article_data['title'],
                        'article_date': article_data['date']
                    }
                )
            else:
                self.logger.info(f"Skipping old article: {article_data['date']}")

        # Pagination - look for next page
        if page < 3 and len(articles_data) > 0:
            next_page = self.find_next_page(response)
            if next_page:
                self.logger.info(f"Found next page: {next_page}")
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse_article_list,
                    meta={'page': page + 1}
                )

    def extract_articles_with_data(self, response):
        """
        Extract articles with titles and dates from bankinform.ru
        """
        articles_data = []

        # Find all article links with the specified class
        article_links = response.css('a.text-decoration-none')

        for link in article_links:
            href = link.css('::attr(href)').get()
            title = link.css('::text').get()

            if href and title and title.strip():
                # Find date - look for time element with date class
                date_element = link.xpath('./following-sibling::time[contains(@class, "date")] | '
                                        '../time[contains(@class, "date")] | '
                                        '../../time[contains(@class, "date")]').get()

                date_text = None
                if date_element:
                    date_selector = scrapy.Selector(text=date_element)
                    date_text = date_selector.css('::text').get()
                else:
                    # Try alternative approach - find time element near the link
                    parent_container = link.xpath('./ancestor::div[1]')
                    if parent_container:
                        time_element = parent_container.xpath('.//time[@class="date"]/text()').get()
                        if time_element:
                            date_text = time_element.strip()

                article_date = self.parse_date_text(date_text) if date_text else None

                full_url = self.clean_url(href)
                if full_url:
                    articles_data.append({
                        'url': full_url,
                        'title': title.strip(),
                        'date': article_date
                    })

        return articles_data

    def parse_date_text(self, date_text):
        """Parse date text to datetime object"""
        if not date_text:
            return None

        clean_text = self.clean_date_text(date_text)
        if not clean_text:
            return None

        # Handle time-only format like "10:12" (means today)
        if re.match(r'^\d{1,2}:\d{2}$', clean_text.strip()):
            # If only time is shown, it means today
            time_parts = clean_text.strip().split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            now = datetime.now()
            return datetime(now.year, now.month, now.day, hour, minute)

        # Try Russian date format like "09 декабря 15:26"
        date_obj = self.parse_russian_date_with_time(clean_text)
        if date_obj:
            return date_obj

        # Try Russian date format
        date_obj = self.parse_russian_date(clean_text)
        if date_obj:
            return date_obj

        # Try relative dates
        date_obj = self.parse_relative_date(clean_text)
        if date_obj:
            return date_obj

        # Try standard date formats
        date_obj = self.parse_standard_date(clean_text)
        if date_obj:
            return date_obj

        return None

    def parse_russian_date_with_time(self, date_str):
        """
        Parse Russian date format with time to datetime object
        Handles formats like: '09 декабря 15:26'
        """
        try:
            # Use regex to extract date and time parts
            pattern = r'(\d{1,2})\s+([а-яё]+)\s+(\d{1,2}):(\d{2})'
            match = re.search(pattern, date_str)

            if match:
                day = int(match.group(1))
                month_ru = match.group(2).lower()
                hour = int(match.group(3))
                minute = int(match.group(4))
                now = datetime.now()
                year = now.year  # Assume current year if not specified

                month_mapping = {
                    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                }

                if month_ru in month_mapping:
                    return datetime(year, month_mapping[month_ru], day, hour, minute)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse Russian date with time '{date_str}': {e}")
            return None

    def parse_russian_date(self, date_str):
        """
        Parse Russian date format to datetime object
        Handles formats like: '27 октября 2025'
        """
        try:
            # Use regex to extract date parts
            pattern = r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})'
            match = re.search(pattern, date_str)

            if match:
                day = int(match.group(1))
                month_ru = match.group(2).lower()
                year = int(match.group(3))

                month_mapping = {
                    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                }

                if month_ru in month_mapping:
                    return datetime(year, month_mapping[month_ru], day)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse Russian date '{date_str}': {e}")
            return None

    def parse_standard_date(self, date_str):
        """Parse standard date formats like DD.MM.YYYY"""
        try:
            # Try DD.MM.YYYY
            pattern1 = r'(\d{1,2})\.(\d{1,2})\.(\d{4})'
            match1 = re.search(pattern1, date_str)
            if match1:
                day = int(match1.group(1))
                month = int(match1.group(2))
                year = int(match1.group(3))
                return datetime(year, month, day)

            # Try YYYY-MM-DD
            pattern2 = r'(\d{4})-(\d{1,2})-(\d{1,2})'
            match2 = re.search(pattern2, date_str)
            if match2:
                year = int(match2.group(1))
                month = int(match2.group(2))
                day = int(match2.group(3))
                return datetime(year, month, day)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse standard date '{date_str}': {e}")
            return None

    def parse_relative_date(self, date_str):
        """Parse relative dates like '1 день назад', '2 часа назад'"""
        try:
            numbers = re.findall(r'\d+', date_str)
            if numbers:
                amount = int(numbers[0])

                if 'день' in date_str or 'дня' in date_str or 'дней' in date_str:
                    return datetime.now() - timedelta(days=amount)
                elif 'час' in date_str or 'часа' in date_str or 'часов' in date_str:
                    return datetime.now() - timedelta(hours=amount)
                elif 'минут' in date_str:
                    return datetime.now() - timedelta(minutes=amount)
                elif 'недел' in date_str:
                    return datetime.now() - timedelta(weeks=amount)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse relative date '{date_str}': {e}")
            return None

    def clean_date_text(self, date_text):
        """Clean and validate date text"""
        if not date_text:
            return None

        date_text = date_text.strip()

        # Remove icons and extra text
        date_text = re.sub(r'[⏰🕒📅]', '', date_text)
        date_text = re.sub(r'\s+', ' ', date_text)

        # Check if it looks like a date
        date_patterns = [
            r'\d{1,2}\s+[а-яё]+\s+\d{4}',
            r'\d{1,2}\.\d{1,2}\.\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}\s+[а-яё]+',
            r'\d+\s+(час|день|дня|дней|минут|недел)'
        ]

        for pattern in date_patterns:
            if re.search(pattern, date_text, re.IGNORECASE):
                return date_text

        return None

    def find_next_page(self, response):
        """Find next page link"""
        next_selectors = [
            'a.next::attr(href)',
            'a[rel="next"]::attr(href)',
            '.pagination a:contains("Далее")::attr(href)',
            '.pagination a:contains("Next")::attr(href)',
            'a:contains("›")::attr(href)',
            'a:contains("»")::attr(href)',
            '.pager-next a::attr(href)'
        ]

        for selector in next_selectors:
            next_page = response.css(selector).get()
            if next_page:
                return self.clean_url(next_page)

        return None

    def clean_url(self, url):
        """Clean and normalize URLs"""
        if not url:
            return None

        # Handle relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin('https://bankinform.ru', url)
        elif not url.startswith('http'):
            url = urljoin('https://bankinform.ru', url)

        # Ensure it's a bankinform.ru URL
        if not url.startswith('https://bankinform.ru/'):
            return None

        return url

    def parse_article(self, response):
        title = response.meta.get('title')
        article_date = response.meta.get('article_date')

        # If title wasn't passed from list page, extract it from article
        if not title:
            title = (response.css('h1::text').get() or
                    response.css('.article-title::text').get() or
                    response.css('title::text').get() or "").strip()

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
            'search_term': 'bankinform-fintech',
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

    def extract_description(self, response):
        """Extract description from article content - first meaningful <p> tag"""

        # Try to find the main article content
        content_selectors = [
            'article p',
            '.article-content p',
            '.post-content p',
            '.content p',
            '.entry-content p',
            '.news-detail p',
            '.text p'
        ]

        for selector in content_selectors:
            paragraphs = response.css(selector)
            for p in paragraphs:
                text = p.css('::text').get()
                if text:
                    clean_text = self.clean_paragraph(text)
                    if clean_text and len(clean_text) > 30:
                        return clean_text

        # Fallback: get any first paragraph
        first_p = response.css('p::text').get()
        if first_p:
            clean_text = self.clean_paragraph(first_p)
            if clean_text:
                return clean_text

        return "Description not available"

    def clean_paragraph(self, text):
        """Clean paragraph text"""
        if not text:
            return ""

        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Filter out unwanted content
        unwanted_patterns = [
            'Подпишитесь',
            'читайте также',
            'реклама',
            'advertisement',
            'Фото:',
            'Фотография:',
            'Источник:',
            'По материалам'
        ]

        for pattern in unwanted_patterns:
            if pattern.lower() in text.lower():
                return ""

        return text
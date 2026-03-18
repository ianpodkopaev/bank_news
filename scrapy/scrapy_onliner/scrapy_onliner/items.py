import scrapy

class ScrapedItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    post_date = scrapy.Field()
    scraped_at = scrapy.Field()

import scrapy


class TbankItem(scrapy.Item):
    title = scrapy.Field()
    full_text = scrapy.Field()
    post_date = scrapy.Field()
    scraped_at = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    processed = scrapy.Field()
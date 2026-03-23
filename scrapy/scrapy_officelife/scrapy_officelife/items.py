import scrapy


class ScrapyOfficelifeItem(scrapy.Item):
    title = scrapy.Field()
    full_text = scrapy.Field()
    post_date = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    scraped_at = scrapy.Field()

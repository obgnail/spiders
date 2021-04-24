# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AnimeItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title       = scrapy.Field()
    badge       = scrapy.Field()
    cover       = scrapy.Field()
    index_show  = scrapy.Field()
    is_finish   = scrapy.Field()
    media_id    = scrapy.Field()
    follow      = scrapy.Field()
    play        = scrapy.Field()
    score       = scrapy.Field()

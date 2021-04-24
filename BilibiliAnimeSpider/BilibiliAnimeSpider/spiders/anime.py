# -*- coding: utf-8 -*-
import scrapy
import json
from BilibiliAnimeSpider.items import AnimeItem


class AnimeSpider(scrapy.Spider):

    name = 'anime'
    allowed_domains = ['https://bangumi.bilibili.com/']
    start_urls = ['https://bangumi.bilibili.com/media/web_api/search/result?season_version=-1&area=-1&is_finish=-1&copyright=-1&season_status=-1&season_month=-1&pub_date=-1&style_id=-1&order=3&st=1&sort=0&page=1&season_type=1&pagesize=20']

    def __init__(self):
    	self.page = 1
    def parse(self, response):
    	item = AnimeItem()
    	for each_anime in json.loads(response.body).get('result').get('data'):
    		order = each_anime.get('order')

    		item['title']      = each_anime.get('title')      # 标题
    		item['badge']      = each_anime.get('badge')      # 是否会员专享
    		item['cover']      = each_anime.get('cover')      # 封面url
    		item['index_show'] = each_anime.get('index_show') # 共几话
    		item['is_finish']  = each_anime.get('is_finish')  # 是否完结
    		item['media_id']   = each_anime.get('media_id')   # 动画的id
    		item['follow']     = order.get('follow')          # 追番数
    		item['play']       = order.get('play')            # 播放数
    		item['score']      = order.get('score')           # 分数

    		yield item

    	self.page += 1
    	next_url = 'https://bangumi.bilibili.com/media/web_api/search/result?season_version=-1&area=-1&is_finish=-1&copyright=-1&season_status=-1&season_month=-1&pub_date=-1&style_id=-1&order=3&st=1&sort=0&page={}&season_type=1&pagesize=20'.format(self.page)

    	if self.page <= 155:
    		yield scrapy.Request(url=next_url,callback=self.parse,dont_filter=True)
    	else:
    		print('-'*100,'end, There are {} pages in all.'.format(self.page-1),'-'*100,sep='\n')


 
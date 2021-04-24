import json

from entity import Item, Request
from spider import SpiderRaw


class Spider(SpiderRaw):
    allowed_domains = ['http://i-remember.fr/']
    start_urls = ['http://i-remember.fr/api/search-posts?ln=en']

    def __init__(self, crawl_page=3):
        self.crawl_page = crawl_page
        self.count_page = 0
        self.count_item = 0

    def parse(self, response):
        res = json.loads(response.content)
        for post in res.get('data').get('posts'):
            item = Item()
            item['created_time'] = post.get('created_at')
            item['id'] = post.get('id')
            item['img'] = post.get('img')
            item['name'] = post.get('name')
            item['text'] = post.get('text')

            self.count_item += 1
            yield item

        self.count_page += 1
        if self.count_page < self.crawl_page:
            # 下一页
            last_id = item['id']
            next_url = f'http://i-remember.fr/api/search-posts?ln=en&lastId={last_id}'
            yield Request(url=next_url, callback=self.parse)
        else:
            print(f'=== had handler {self.count_item} item ===')


if __name__ == '__main__':
    Spider().run(max_threads=4)

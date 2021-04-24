from base import DomSpider
from parsers import Parser


class MyWebSpider(DomSpider):
    def parse(self, data):
        return Parser(data).xpath('//a[@href]/text()')


my_web = MyWebSpider(method='get', url='http://106.15.94.49/download/software/')
res = my_web.crawl()
print(res)

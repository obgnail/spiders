from requesters import Request


class BaseSpider:
    def request(self, method, url, **kwargs):
        raise NotImplementedError

    def parse(self, data):
        raise NotImplementedError

    def crawl(self):
        raise NotImplementedError


class Spider(BaseSpider):
    def __init__(self, method, url, **kwargs):
        self.method = method
        self.url = url
        self.kwargs = kwargs

    def request(self, method, url, **kwargs):
        resp = Request.request(method, url, **kwargs)
        if resp:
            return resp

    def crawl(self):
        resp = self.request(self.method, self.url, **self.kwargs)
        if resp:
            return self.parse(resp)


class DomSpider(Spider):
    def request(self, method, url, **kwargs):
        data = super().request(self.method, self.url, **kwargs)
        if data:
            return data.text


class JsonSpider(Spider):
    def request(self, method, url, **kwargs):
        data = super().request(self.method, self.url, **kwargs)
        if data:
            return data.json()

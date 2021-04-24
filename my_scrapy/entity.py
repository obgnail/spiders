import asyncio

import aiohttp


class Request:
    def __init__(self, url, callback=None, meta=None, dont_filter=False,
                 headers=None, cookies=None, proxies=None):
        self.url = url
        self.callback = callback
        self.headers = headers
        self.cookies = cookies
        self.proxies = proxies
        self.meta = meta
        self.dont_filter = dont_filter

    def get_url(self):
        return self.url

    def set_headers(self, **kwargs):
        self.headers.update(kwargs)

    def set_cookies(self, **kwargs):
        self.cookies.update(kwargs)


class Scheduler:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        self.q = asyncio.Queue()

    def push_request(self, request):
        self.q.put_nowait(request)

    async def get_request(self):
        return (await self.q.get())

    def empty(self):
        return self.q.empty()


scheduler = Scheduler()


class Response:
    def __init__(self, content, callback=None, meta=None, cookies=None):
        self.content = content
        self.callback = callback
        self.meta = meta
        self.cookies = cookies


class Downloader:
    @classmethod
    async def run(cls,request):
        # 下载
        async with aiohttp.ClientSession() as sesssion:
            try:
                async with sesssion.get(url=request.url, headers=request.headers,
                                        cookies=request.cookies) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        # 返回Response对象
                        return Response(content=content, callback=request.callback,
                                        cookies=request.cookies, meta=request.meta)
                    else:
                        print(f'--- request status error:{request.url} ---')
            except aiohttp.ClientConnectionError:
                print(f'--- requests connection error:{request.url} ---')


class Item:
    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, item):
        return self.__dict__[item]

    def send_to_pipe(self):
        pass

    def handle(self):
        print(self.__dict__)


class ItemPipeline:
    def __init__(self, item):
        self.item = item

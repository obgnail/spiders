import asyncio
import re
import aiohttp

from datetime import datetime
from lxml import etree


class DomainExpiryDateGetter:
    def __init__(self, domain):
        self.result = None
        self.q = asyncio.Queue(loop=asyncio.new_event_loop())
        # 注册爬取的网站及其回调的解析函数
        self.callback_dict = {
            f'http://whois.chinaz.com/{domain}': self.parse_chinaz,
            f'http://whois.xinnet.com/domains_srv/{domain}': self.parse_xinnet,
            # f'http://whois.webmasterhome.cn/?domain={domain}': self.parse_webmasterhome,
        }

        self.headers = {
            'user-agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/70.0.3538.77 Safari/537.36'
        }

    async def request(self, url):
        async with aiohttp.ClientSession() as sesssion:
            try:
                async with sesssion.get(url=url, headers=self.headers) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        print(f'--- request status error:{url} ---')
            except aiohttp.ClientConnectionError:
                print(f'--- requests connection error:{url} ---')

    def parse_chinaz(self, resp):
        ele = etree.HTML(resp).xpath('//a[@id="update_a2"]/parent::*/span')
        if ele:
            expirydate = ele[0].text
            return self.to_timestamp(datetime.strptime(expirydate,
                                                       "%Y年%m月%d日"))

    def parse_xinnet(self, resp):
        ret = re.search(r'Registry Expiry Date: (.*?)<br/>', resp)
        if ret:
            expirydate = ret.group(1)
            return self.to_timestamp(
                datetime.strptime(expirydate, "%Y-%m-%dT%H:%M:%SZ"))

    def parse_webmasterhome(self, resp):
        ...

    def to_timestamp(self, t):
        return int(t.timestamp())

    async def crawl_domain(self, url, parser):
        """
        爬取
        """
        resp = await self.request(url)
        if resp:
            expirydate = parser(resp)
            return expirydate

    async def handle_tasks(self, task_id):
        """
        处理爬取队列
        """
        while not self.q.empty():
            url, parser = await self.q.get()
            print(
                f'======= thread No.{task_id + 1} had started ,request: {url} ======='
            )
            # 该域名的过期时间
            response = await self.crawl_domain(url, parser)
            if response:
                self.result = response
                break

    def run(self, max_threads=3):
        for url, parser in self.callback_dict.items():
            # 将待爬取的url和回调函数放入队列
            self.q.put_nowait((url, parser))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [self.handle_tasks(task_id) for task_id in range(max_threads)]
        loop.run_until_complete(asyncio.wait(tasks))


def domain_spider(domain, max_threads=3):
    d = DomainExpiryDateGetter(domain)
    d.run(max_threads)
    return d.result

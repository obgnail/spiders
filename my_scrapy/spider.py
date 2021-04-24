import json
import re
import asyncio

from entity import Request, scheduler, Downloader, Item


class SpiderRaw:
    allowed_domains = []
    start_urls = []

    def parse(self, response):
        pass

    def push_request(self, request):
        """
        将request放入调度器
        """
        if self.allowed_domains:
            for allowed_domain in self.allowed_domains:
                # 如果开启不筛选或者匹配成功
                if request.dont_filter or re.search(allowed_domain, request.url):
                    scheduler.push_request(request)

    def get_start_request(self):
        """
        将初始url放入调度器
        """
        for start_url in self.start_urls:
            self.push_request(Request(start_url))

    async def crawl(self,request):
        """
        爬取单个request
        """
        # 开始下载，获取response
        response = await Downloader.run(request)
        if response:
            # 为response回调解析函数，解析函数返回item或者Request
            if response.callback:
                ret = response.callback(response)
            else:
                # 默认回调parse函数
                ret = self.parse(response)
            # 从回调函数获取Request或者Item
            for req_or_item in ret:
                if isinstance(req_or_item, Request):
                    # 将新的Request放入调度器中
                    self.push_request(req_or_item)
                elif isinstance(req_or_item, Item):
                    # 交由Item的处理函数解决
                    req_or_item.handle()
                else:
                    raise Exception('spider parse method yield error')

    async def handle_tasks(self, task_id):
        """
        不断的从调度器拿到Requst,传给crawl,让crawl去爬取
        """
        while True:
            # 从scheduler中取出Request对象
            request = await scheduler.get_request()
            print(f'======= thread No.{task_id + 1} had started ,crawling {request.url} =======')
            await self.crawl(request)


    def run(self, max_threads=3):
        # 将start_urls放入调度器中
        self.get_start_request()

        loop = asyncio.get_event_loop()
        tasks = [self.handle_tasks(task_id) for task_id in range(max_threads)]
        loop.run_until_complete(asyncio.wait(tasks))

        print('---------- end ----------')

import re
import logging
import asyncio

import aiohttp
from pyquery import PyQuery as pq


class NhentaiSpider:
    def __init__(self, language, max_pages, max_threads):
        self.language = language
        self.max_pages = max_pages
        self.max_threads = max_threads

        self.results = []
        self.q = asyncio.Queue()

        self.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
        self.detail_url_pattern = re.compile(r'galleries\/(\d+)\/(\d+)t', re.S)
        self.language_pattern_dict = {
            'All': r'^.*$',
            'Chinese': r'^.*([Cc]hinese|汉化|漢化).*$',
            'English': r'^.*([Ee]nglish).*$',
            'Japan': r'^((?<![Cc]hinese|[Ee]nglish).)*$'
        }

    async def __request_dom(self, url):
        async with aiohttp.ClientSession() as sesssion:
            try:
                async with sesssion.get(url=url, headers=self.headers) as resp:
                    if resp.status == 200:
                        return (await resp.text())
                    else:
                        print('request status error')
            except aiohttp.ClientConnectionError:
                print('requests connection error')

    def __parse_index(self, index_html):
        pattern = re.compile(self.language_pattern_dict[self.language], re.S)
        div_tags = pq(index_html)('.container.index-container .gallery').items()
        for div_tag in div_tags:
            try:
                title = pattern.search(div_tag('.caption').text()).group()
            except AttributeError:
                pass
            else:
                x = {
                    'title': title,
                    'commic_url': 'https://nhentai.net' + div_tag('a[class="cover"]').attr('href'),
                    'face_img_url': div_tag('noscript img').attr('src'),
                    'pages_url': [],
                }
                self.results.append(x)

    def __parse_detail(self, detail_html):
        div_tags = pq(detail_html)('.thumb-container a img').items()
        commic_pages_list = []
        for div_tag in div_tags:
            png_url = div_tag.attr('data-src')
            if png_url:
                result_url = self.detail_url_pattern.search(png_url).groups()

                img_url = 'https://i.nhentai.net/galleries/{}/{}.jpg'.format(*result_url)
                commic_pages_list.append(img_url)
        return commic_pages_list

    async def get_results(self, url):
        '''抓取单个url'''
        html = await self.__request_dom(url)
        if html:
            self.__parse_index(html)

            for each_commic in self.results:
                each_commic_url = each_commic['commic_url']
                detail_html = await self.__request_dom(each_commic_url)
                commic_pages_list = self.__parse_detail(detail_html)
                each_commic['pages_url'] = commic_pages_list

    async def handle_tasks(self, task_id):
        while not self.q.empty():
            current_url = await self.q.get()
            try:
                task_status = await self.get_results(current_url)
            except Exception as e:
                logging.exception('Error for {}'.format(current_url), exc_info=True)

    def run(self):
        for page in range(1, self.max_pages + 1):
            url = f'https://nhentai.net/?page={page}'
            self.q.put_nowait(url)

        loop = asyncio.get_event_loop()
        tasks = [self.handle_tasks(task_id) for task_id in range(self.max_threads)]
        loop.run_until_complete(asyncio.wait(tasks))


def main():
    # 抓取本子的语言(其他语言丢弃)
    # 填入All/Chinese/Japan/English
    language = 'Chinese'
    max_page = 5
    max_threads = 2

    nhentaispider = NhentaiSpider(language, max_page, max_threads)
    nhentaispider.run()
    print(nhentaispider.results)


if __name__ == '__main__':
    main()

import requests
import re
import os
import time


def return_vaild_name(title):
    result = re.sub(r'[\\/:*?"<>|\r\n]+', '_', title)
    return result


def request_dom(url):
    res = requests.get(url, proxies={'https': '127.0.0.1:7890'})
    if res.status_code == 200:
        return res.text


def parse_dom_to_page_num(text):
    res = re.search(r'Pages:.*?<span class="name">(\d+)</span>', text, re.S)
    if res:
        return res.group(1)


def parse_dom_to_galleries_num(text):
    res = re.search(r'<meta itemprop="image".*?galleries/(\d+)/cover.jpg', text, re.S)
    if res:
        return res.group(1)


def parse_dom_to_name(text):
    res = re.search(
        r'<span class="before">(.*?)</span><span class="pretty">(.*?)</span><span class="after">(.*?)</span>', text,
        re.S)
    if res:
        return ''.join(res.groups())

def get_download_urls(galleries_num, page_num):
    urls = ['https://i.nhentai.net/galleries/{}/{}.jpg'.format(galleries_num, page) for page in range(1, int(page_num) + 1)]
    return urls


def download_img( galleries_num, page_num, file_name):
    file_name = return_vaild_name(file_name)

    file_url = f'download/{file_name}'

    if not os.path.exists(file_url):
        os.mkdir(file_url)

    print(f'======开始下载{file_url}')
    for page in range(1, int(page_num) + 1):
        url = 'https://i.nhentai.net/galleries/{}/{}.jpg'.format(galleries_num, page)
        res = requests.get(url, proxies={'https': '127.0.0.1:7890'})
        if res.status_code == 200:
            data = res.content

            img_url = '{}/{}.jpg'.format(file_url, page)
            with open(img_url, 'wb') as f:
                if f.write(data):
                    print(r'已存储到:{}/{}.jpg,一共{}页'.format(file_name, page,page_num))
                else:
                    print('--------存储失败:', file_name)
        time.sleep(1)


def main(url):
    text = request_dom(url)
    page_num = parse_dom_to_page_num(text)
    galleries_num = parse_dom_to_galleries_num(text)
    name = parse_dom_to_name(text)
    print('---start---',galleries_num, page_num, name)
    download_img(galleries_num, page_num, name)
    print('---end---')


if __name__ == '__main__':
    commic_ids = [304632]

    for commic_id in commic_ids:
        url = f'https://nhentai.net/g/{commic_id}/'
        main(url)
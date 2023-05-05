import requests
import time
import math
import os
import re
import zipfile
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _request(url, proxy='localhost:7890'):
    return requests.get(url=url, proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'}, verify=False)


def _get_rjcode_with_subtitle(page, proxy):
    url = f'https://api.asmr-100.com/api/works?order=dl_count&sort=desc&page={page}&subtitle=1'
    response = _request(url=url, proxy=proxy)
    result = response.json()

    info = result['pagination']

    codes = []
    for i in result['works']:
        code = str(i['id'])
        if len(code) < 6:
            code = '0' * (6 - len(code)) + code  # rjcode 最少八位数
        codes.append('RJ' + code)

    return {
        'current_page': info['currentPage'],
        'page_size': info['pageSize'],
        'total_count': info['totalCount'],
        'rjcode': codes
    }


def get_rjcode_with_subtitle(proxy='localhost:7890'):
    result = []
    page = 1
    while True:
        d = _get_rjcode_with_subtitle(page, proxy)
        max_page = math.ceil(d['total_count'] / d['page_size'])

        print(f'--- get rj with subtitle ({page}/{max_page})')

        result.extend(d['rjcode'])

        if max_page == page:
            break
        else:
            page += 1

        time.sleep(0.5)

    return result


def _get_rj_from_local(path):
    s = set()
    for filename in os.listdir(path):
        filename = filename.strip().upper().removesuffix('.ZIP')
        s.add(filename)
    return s


def query_tracks(rjcode, proxy='localhost:7890'):
    code = rjcode.upper().removeprefix('RJ')
    url = f'https://api.asmr-100.com/api/tracks/{code}'
    response = _request(url=url, proxy=proxy)
    result = response.json()
    return result


def get_lrc_file(folder):
    result = []
    for ele in folder:
        if ele['type'] == 'folder':
            res = get_lrc_file(ele['children'])
            if len(res) != 0:
                result.extend(res)
        elif ele['type'] == 'text':
            title = ele['title'].upper()
            if title.endswith('.LRC') or title.endswith('.ASS'):
                result.append({
                    'title': ele['title'],
                    'url': ele['mediaDownloadUrl'],
                })

    return result


def filter_lrc(lrc_files):
    s = set()
    result = []

    for file in lrc_files:
        if file['title'] in s:
            pass
        else:
            s.add(file['title'])
            result.append(file)

    return result


def request_lrc(url, proxy):
    resp = _request(url=url, proxy=proxy)
    content = resp.text

    return content


def verify_name(title):
    result = re.sub(r'[\\/:*?"<>|\r\n]+', '_', title)
    return result


def zip_dir(dirpath, outFullName):
    zip = zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        fpath = path.replace(dirpath, '')

        for filename in filenames:
            zip.write(os.path.join(path, filename), os.path.join(fpath, filename))
    zip.close()


def download_save_lrc(rjcode, proxy='localhost:7890'):
    resp = query_tracks(rjcode, proxy)
    result = get_lrc_file(resp)
    lrcs = filter_lrc(result)

    dir = os.path.join(os.getcwd(), rjcode)
    if not os.path.exists(dir):
        os.makedirs(dir)

    for lrc in lrcs:
        print('--- downloading', rjcode, '--', lrc['title'])
        name = verify_name(lrc['title'])
        path = os.path.join(dir, name)
        context = request_lrc(lrc['url'], proxy)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(context)

    zip_dir(dir, dir + '.zip')


def filter_rjcode(ids):
    path = r'D:\myshare\_local_samba\asmr_lrc'
    rjcodes = _get_rj_from_local(path)
    target = [id for id in ids if id not in rjcodes]
    return target


def main():
    proxy = 'localhost:7890'

    ids = get_rjcode_with_subtitle(proxy)
    ids = filter_rjcode(ids)

    print('--- tot:', len(ids))
    for idx, rjcode in enumerate(ids):
        print(f'--- handle({idx + 1}/{len(ids)}): {rjcode}')
        download_save_lrc(rjcode, proxy)


if __name__ == '__main__':
    main()

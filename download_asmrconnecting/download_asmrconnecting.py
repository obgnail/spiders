import requests
import time
import os
import re
import json

import urllib3

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
}


def _post(url, data, proxy='localhost:7890'):
    _proxy = None if proxy is None else {
        'http': f'http://{proxy}', 'https': f'http://{proxy}'}
    i = 0
    while i < 3:
        try:
            resp = requests.post(url=url, json=data, proxies=_proxy, headers=headers)
            return resp
        except (urllib3.exceptions.MaxRetryError, requests.exceptions.ProxyError) as e:
            print(e)
            time.sleep(5)
            i += 1


def _get(url, proxy='localhost:7890'):
    _proxy = None if proxy is None else {
        'http': f'http://{proxy}', 'https': f'http://{proxy}'}
    i = 0
    while i < 3:
        try:
            resp = requests.get(url=url, proxies=_proxy, headers=headers)
            return resp
        except (urllib3.exceptions.MaxRetryError, requests.exceptions.ProxyError) as e:
            print(e)
            time.sleep(5)
            i += 1


def get_page_info(path, proxy):
    print('get page:', path)

    url = 'https://asmrconnecting.xyz/api/fs/list'
    _json = {"path": path, "password": "",
             "page": 1, "per_page": 0, "refresh": False}
    resp = _post(url, _json, proxy=proxy)
    j = resp.json()
    if j['code'] != 200:
        raise f'{path}: {j["message"]}'

    return j['data']['content']


def get_file_info(path, proxy):
    print('get file:', path)

    url = 'https://asmrconnecting.xyz/api/fs/get'
    _json = {"path": path, "password": ""}
    resp = _post(url, _json, proxy=proxy)
    j = resp.json()
    if j['code'] != 200:
        raise f'{path}: {j["message"]}'
    return j['data']


def _get_local_rjcode(path):
    local = set()
    for filename in os.listdir(path):
        filename = filename.strip().upper().removesuffix('.ZIP')
        local.add(filename)
    return local


def verify_name(title):
    result = re.sub(r'[\\/:*?"<>|\r\n]+', '_', title)
    return result


def _get_remote_rjcode(index_path, proxy):
    index_page = get_page_info(path=index_path, proxy=proxy)

    result = {}
    for rjcode_range in index_page:
        title = rjcode_range['name']
        next_path = f'{index_path}/{title}'
        rjcode_list = get_page_info(path=next_path, proxy=proxy)
        result[next_path] = rjcode_list
        time.sleep(2)

    return result


def _filter(local_rjcode_list, remote_rjcode_list):
    result = []

    for rjcode_range, rjs in remote_rjcode_list.items():
        for rj in rjs:
            name = rj['name'].upper()
            if name not in local_rjcode_list:
                rj['path'] = rjcode_range + "/" + rj["name"]
                result.append(rj)
    return result


def record_rjcode(rj_list, filename="record_rjcode.json"):
    data = {"data": rj_list}
    json_object = json.dumps(data, indent=4)

    with open(filename, "w") as outfile:
        outfile.write(json_object)


def read_record_rjcode(filename="record_rjcode.json"):
    with open(filename, 'r') as openfile:
        json_object = json.load(openfile)
    return json_object['data']


def _mkdir(dirname):
    dir = os.path.join(os.getcwd(), dirname)
    if not os.path.exists(dir):
        os.makedirs(dir)
    return dir


ten_million = 1024 * 1024 * 10


def is_lrc(file):
    filename = file['name'].upper()

    b = (
        file['size'] <= ten_million
        and ('LRC' in filename or 'ASS' in filename)
        # and (not filename.endswith('.PNG') and not filename.endswith('.JPG') and not filename.endswith('.JPEG'))
        and ('标记文件' not in filename)
        and ('PASSWORD' not in filename)
    )

    return b


def search_lrc_file(rj, proxy):
    lrc_files = []

    remote_files = get_page_info(path=rj['path'], proxy=proxy)

    for file in remote_files:
        if is_lrc(file):
            lrc_files.append(file)

    return lrc_files


def download_rj(rj, proxy):
    lrc_files = search_lrc_file(rj, proxy)

    if len(lrc_files) == 0:
        return False

    rj_dir = _mkdir(rj['name'])

    for lrc_file in lrc_files:
        lrc_path = rj["path"] + "/" + lrc_file["name"]
        file_info = get_file_info(path=lrc_path, proxy=proxy)

        resp = _get(file_info['raw_url'])
        content = resp.content

        lrc_name = verify_name(file_info['name'])
        path = os.path.join(rj_dir, lrc_name)
        with open(path, 'bw') as f:
            f.write(content)

        time.sleep(0.5)

    return True


def get_rjcode_from_network(proxy):
    local_path = r'D:\myshare\_local_samba\asmr_lrc'
    index_path = '/音声/汉化'

    local_rjcode_list = _get_local_rjcode(local_path)
    remote_rjcode_list = _get_remote_rjcode(index_path, proxy)

    rj_list = _filter(local_rjcode_list, remote_rjcode_list)

    record_rjcode(rj_list)

    return rj_list


def get_rjcode_from_local():
    return read_record_rjcode()


def is_zip_file(filename):
    filename = filename.lower()
    if filename.endswith('.7z') or filename.endswith('.rar') or filename.endswith('.zip'):
        return True
    return False


def _unzip(zip_file, password):
    zip_cmd = r'D:\software\7-Zip\7z.exe'
    unzip_option = 'x'
    auto = '-y'

    zip_file_dir = os.path.dirname(zip_file)
    dir = os.path.join(zip_file_dir, os.path.splitext(zip_file)[0])
    if not os.path.exists(dir):
        os.makedirs(dir)

    cmd = f'{zip_cmd} {unzip_option} {auto} -p"{password}" "{zip_file}" -o"{dir}"'
    f = os.popen(cmd)
    result = f.read()

    if 'Everything is Ok' in result:
        return True
    return False


password_list = [
    '',
    '野兽先辈',
    'Kathleens',
    '转载须同意，贩卖死全家',
    '橙澄子汉化组',
    '风花雪月汉化组',
    'TchiWscien_LGBK_Non_Ythcien',
]


def unzip(zip_file):
    pw_list = password_list.copy()
    match_obj = re.search(r'\((.+)\)', zip_file, re.M | re.I)
    if match_obj:
        pw = match_obj.group(1)
        pw_list.insert(0, pw)

    for password in pw_list:
        if _unzip(zip_file, password):
            return True
    return False


def _decompression(file):
    if os.path.exists(file):
        if unzip(file):
            os.remove(file)
            return True
        else:
            print('--- decompression error: ', file)
    else:
        msg = "error file path: " + file
        raise BaseException(msg)
    return False


def decompression(rj):
    rj_dir = os.path.join(os.getcwd(), rj['name'])

    for filename in os.listdir(rj_dir):
        path = os.path.join(rj_dir, filename)
        if is_zip_file(path):
            ok = _decompression(path)
            if ok:
                return True

    return False


def rename_dir(rj_dir, rj):
    children = os.listdir(rj_dir)
    if len(children) != 1:
        return

    path = os.path.join(rj_dir, children[0])
    if os.path.isdir(path):
        new_name = os.path.join(rj_dir, rj['name'])
        os.rename(path, new_name)
        return rename_dir(new_name, rj)


def print_error_rjcode(error_files):
    if len(error_files) != 0:
        record_rjcode(error_files, 'error_rjcode.json')
        print('********** error file:')
        for file in error_files:
            print(file)


def download():
    proxy = 'localhost:7890'

    rj_list = get_rjcode_from_network(proxy)
    # rj_list = get_rjcode_from_local()

    print("********** tot:", len(rj_list))

    error_files = []

    try:
        for idx, rj in enumerate(rj_list):
            print(
                '********** downloading:{} ({}/{})'.format(rj['name'], idx + 1, len(rj_list)))
            if not download_rj(rj, proxy):
                error_files.append(rj)
            else:
                ok = decompression(rj)
                if not ok:
                    print('--- decompression is not ok:', rj)
                else:
                    rj_dir = os.path.join(os.getcwd(), rj['name'])
                    rename_dir(rj_dir, rj)

            time.sleep(1.5)
    finally:
        print_error_rjcode(error_files)


def main():
    download()


if __name__ == '__main__':
    main()

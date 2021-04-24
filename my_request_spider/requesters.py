import requests

from logger import logger


class Request:
    max_try = 3
    time_out = 10
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/70.0.3538.77 Safari/537.36'}

    @classmethod
    def request(cls, method, url, **kwargs):
        for _ in range(cls.max_try):
            try:
                response = requests.request(
                    method, url, headers=cls.headers,
                    timeout=cls.time_out,
                    **kwargs
                )
            except ConnectionError:
                logger.error(f'{url} ConnectionError')
            else:
                if response.status_code == 200:
                    return response
                else:
                    logger.error(f'{url} status: {response.status_code}')

    @classmethod
    def get(cls, url, params=None, **kwargs):
        return cls.request('get', url, params=params, **kwargs)

    @classmethod
    def post(cls, url, json=None, **kwargs):
        return cls.request('post', url, json=json, **kwargs)

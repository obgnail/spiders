import logging

logger = logging.getLogger(__name__)

#
# def logging_deco(func, logger_format):
#     def inner(method, url, **kwargs):
#         # logger.info(logger_format.format(url=url))
#         print(123123123)
#         return func(method, url, **kwargs)
#
#     return inner
#
#
#
# def request_logging_deco(func):
#     return logging_deco(func, logger_format='crawling url : {url}')
#
#
# def parse_logging_deco(func):
#     return logging_deco(func, logger_format='parsing url : {url}')
#
#
# @parse_logging_deco
# def parse(data):
#     print(data)
#
# parse('hyl')
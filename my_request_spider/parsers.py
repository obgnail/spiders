import re
from lxml import etree
from pyquery import PyQuery as pq


class ReParserMixin:
    def _re_parse(self, func, wb_data, pattern):
        return getattr(re.compile(pattern), func)(wb_data)

    def re_finditer(self, wb_data, pattern):
        yield from self._re_parse('finditer', wb_data, pattern)

    def re_findall(self, wb_data, pattern):
        return self._re_parse('findall', wb_data, pattern)

    def re_match(self, wb_data, pattern):
        return self._re_parse('match', wb_data, pattern)

    def re_search(self, wb_data, pattern):
        return self._re_parse('search', wb_data, pattern)


class XpathParserMixin:
    def xpath_to_ele(self, wb_data, xpath):
        yield from etree.HTML(wb_data).xpath(xpath)

    def xpath_to_ele_list(self, wb_data, xpath):
        return list(self.xpath_to_ele(wb_data, xpath))


class CssParserMixin:
    def css_to_ele(self, wb_data, css):
        yield from pq(wb_data)(css).items()

    def css_to_ele_list(self, wb_data, css):
        return list(self.css_to_ele(wb_data, css))


class JsonParserMixin:
    def json_to_text(self, wb_data, *fields):
        for field in fields:
            wb_data = wb_data.get(field)
        return wb_data


class BaseParser(ReParserMixin,
                 XpathParserMixin,
                 CssParserMixin,
                 JsonParserMixin):

    def __init__(self, wb_data):
        self.wb_data = wb_data

    def xpath(self, xpath):
        return self.xpath_to_ele_list(self.wb_data, xpath)

    def css(self, css):
        return self.xpath_to_ele_list(self.wb_data, css)

    def re(self, re_stirng):
        return self.re_findall(self.wb_data, re_stirng)


class Parser(BaseParser):
    pass

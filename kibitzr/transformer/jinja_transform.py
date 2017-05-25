import logging
import json

import six

from .utils import bake_parametrized
from .html import deep_recursion, SoupOps


logger = logging.getLogger(__name__)


def jinja_transform(code, content, conf):
    from jinja2 import Environment, TemplateError
    html = LazyHTML(content)
    xml = LazyXML(content)
    context = {
        'conf': conf,
        'content': content,
        'lines': content.splitlines(),
        'json': LazyJSON(content),
        'css': html.css,
        'xpath': xml.xpath,
    }
    environment = Environment()
    environment.filters['text'] = text_filter
    template = environment.from_string(code)
    try:
        return True, template.render(context)
    except TemplateError:
        logger.warning("Jinja transform failed", exc_info=True)
        return False, None


def text_filter(html):
    if isinstance(html, list):
        html = "".join(html)
    ok, content = SoupOps.extract_text(html)
    if ok:
        return content
    else:
        raise RuntimeError("Extract text failed")


class LazyJSON(object):
    def __init__(self, content):
        self.text = content
        self._json = None

    @property
    def json(self):
        if self._json is None:
            self._json = json.loads(self.text)
        return self._json

    def __getitem__(self, key):
        return self.json[key]


class LazyHTML(object):
    def __init__(self, content):
        self.html = content
        self._soup = None

    @property
    def soup(self):
        from bs4 import BeautifulSoup
        if self._soup is None:
            self._soup = BeautifulSoup(self.html, "html.parser")
        return self._soup

    def css(self, selector):
        with deep_recursion():
            elements = self.soup.select(selector)
            result = [six.text_type(x)
                      for x in elements]
            return result


class LazyXML(object):
    def __init__(self, content):
        from lxml import etree
        self.xml = content
        self._root = None
        self.etree = etree

    @property
    def root(self):
        if self._root is None:
            self._root = self.etree.fromstring(
                self.xml,
                parser=self.etree.HTMLParser(),
            )
        return self._root

    def xpath(self, selector):
        elements = self.root.xpath(selector)
        return [
            self.etree.tostring(
                element,
                method='html',
                pretty_print=True,
                encoding='unicode',
            )
            for element in elements
        ]


def register():
    return {
        'jinja': bake_parametrized(jinja_transform, pass_conf=True)
    }

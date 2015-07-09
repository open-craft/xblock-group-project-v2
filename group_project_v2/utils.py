# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime
import xml.etree.ElementTree as ET
from lazy.lazy import lazy
from xblock.core import XBlock
from xblock.fragment import Fragment

from xblockutils.resources import ResourceLoader


log = logging.getLogger(__name__)  # pylint: disable=invalid-name
loader = ResourceLoader(__name__)  # pylint: disable=invalid-name


class DottableDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


def parse_date(date_string):
    split_string = date_string.split('/')
    return date(int(split_string[2]), int(split_string[0]), int(split_string[1]))


def inner_html(node):
    if node is None:
        return None

    tag_length = len(node.tag)
    return outer_html(node)[tag_length + 2:-1 * (tag_length + 3)]


def outer_html(node):
    if node is None:
        return None

    html = ET.tostring(node, 'utf-8', 'html').strip()
    if len(node.findall('./*')) == 0 and html.index('>') == len(html) - 1:
        html = html[:-1] + ' />'

    return html


def build_date_field(json_date_string_value):
    """ converts json date string to date object """
    try:
        return datetime.strptime(
            json_date_string_value,
            '%Y-%m-%dT%H:%M:%SZ'
        )
    except ValueError:
        return None


def format_date(date_value):
    fmt = "%b %d" if date_value.year == date.today().year else "%b %d %Y"
    return date_value.strftime(fmt)  # TODO: not l10n friendly


# Make '_' a no-op so we can scrape strings
def gettext(text):
    return text


class ChildrenNavigationXBlockMixin(object):
    @lazy
    def _children(self):
        return [self.runtime.get_block(child_id) for child_id in self.children]

    def _get_children_by_category(self, child_category):
        return [child for child in self._children if child.category == child_category]

    def get_children_fragment(self, context, view='student_view'):
        fragment = Fragment()

        for child in self._children:
            child_fragment = child.render(view, context)
            fragment.add_frag_resources(child_fragment)
            fragment.add_content(child_fragment.content)

        return fragment
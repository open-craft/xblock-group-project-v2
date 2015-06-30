# -*- coding: utf-8 -*-
#

# Imports ###########################################################

import logging
import pkg_resources

from datetime import date, datetime

import xml.etree.ElementTree as ET

from django.template import Context, Template
from xblockutils.resources import ResourceLoader

# Globals ###########################################################

log = logging.getLogger(__name__)  # pylint: disable=invalid-name
loader = ResourceLoader(__name__)  # pylint: disable=invalid-name

# Functions #########################################################

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

    return ET.tostring(node, 'utf-8', 'html').strip()


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
    fmt = "%B %d" if date_value.year == date.today().year else "%b %d %Y"
    return date_value.strftime(fmt)  # TODO: not l10n friendly


# Make '_' a no-op so we can scrape strings
def gettext(text):
    return text

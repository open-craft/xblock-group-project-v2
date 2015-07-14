# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime
from django.conf import settings
import xml.etree.ElementTree as ET
from xblock.fragment import Fragment

from xblockutils.resources import ResourceLoader


log = logging.getLogger(__name__)  # pylint: disable=invalid-name
loader = ResourceLoader(__name__)  # pylint: disable=invalid-name


ALLOWED_OUTSIDER_ROLES = getattr(settings, "ALLOWED_OUTSIDER_ROLES", None)
if ALLOWED_OUTSIDER_ROLES is None:
    ALLOWED_OUTSIDER_ROLES = ["assistant"]


class OutsiderDisallowedError(Exception):
    def __init__(self, detail):
        self.value = detail
        super(OutsiderDisallowedError, self).__init__()

    def __str__(self):
        return "Outsider Denied Access: {}".format(self.value)

    def __unicode__(self):
        return u"Outsider Denied Access: {}".format(self.value)


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


def make_key(*args):
    return ":".join([str(a) for a in args])


def mean(value_array):
    if not value_array:
        return None

    try:
        numeric_values = [float(v) for v in value_array]
        return float(sum(numeric_values) / len(numeric_values))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        log.warning(exc.message)
        return None


def outsider_disallowed_protected_view(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OutsiderDisallowedError as ode:
            error_fragment = Fragment()
            error_fragment.add_content(
                loader.render_template('/templates/html/loading_error.html', {'error_message': unicode(ode)}))
            error_fragment.add_javascript(loader.load_unicode('public/js/group_project_error.js'))
            error_fragment.initialize_js('GroupProjectError')
            return error_fragment

    return wrapper


def outsider_disallowed_protected_json_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OutsiderDisallowedError as ode:
            return {
                'result': 'error',
                'message': ode.message
            }

    return wrapper


NO_EDITABLE_SETTINGS = gettext(u"This XBlock does not contain any editable settings")

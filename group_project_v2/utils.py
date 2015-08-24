# -*- coding: utf-8 -*-
import functools
import logging
from datetime import date, datetime
from django.conf import settings
import xml.etree.ElementTree as ET
from django.utils.safestring import mark_safe
from lazy.lazy import lazy

from xblock.fragment import Fragment

from xblockutils.resources import ResourceLoader


log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)


ALLOWED_OUTSIDER_ROLES = getattr(settings, "ALLOWED_OUTSIDER_ROLES", None)
if ALLOWED_OUTSIDER_ROLES is None:
    ALLOWED_OUTSIDER_ROLES = ["assistant"]


# Make '_' a no-op so we can scrape strings
def gettext(text):
    return text


NO_EDITABLE_SETTINGS = gettext(u"This XBlock does not contain any editable settings")
MUST_BE_OVERRIDDEN = gettext(u"Must be overridden in inherited class")


# TODO: collect all constants here?
class Constants(object):
    ACTIVATE_BLOCK_ID_PARAMETER_NAME = 'activate_block_id'
    CURRENT_STAGE_ID_PARAMETER_NAME = 'current_stage'


class HtmlXBlockProxy(object):
    CATEGORY = 'html'
    STUDIO_LABEL = gettext(u"HTML")


class DiscussionXBlockProxy(object):
    CATEGORY = "discussion-forum"
    STUDIO_LABEL = gettext(u"Discussion")


class OutsiderDisallowedError(Exception):
    def __init__(self, detail):
        self.value = detail
        super(OutsiderDisallowedError, self).__init__()

    def __str__(self):
        return "Outsider Denied Access: {}".format(self.value)

    def __unicode__(self):
        return u"Outsider Denied Access: {}".format(self.value)


def parse_date(date_string):
    split_string = date_string.split('/')
    return date(int(split_string[2]), int(split_string[0]), int(split_string[1]))


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
        return datetime.strptime(json_date_string_value, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        return None


def format_date(date_value):
    fmt = "%b %d" if date_value.year == date.today().year else "%b %d %Y"
    return date_value.strftime(fmt)  # TODO: not l10n friendly


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
    @functools.wraps(func)
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


def outsider_disallowed_protected_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OutsiderDisallowedError as ode:
            return {
                'result': 'error',
                'message': ode.message
            }

    return wrapper


def key_error_protected_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError as exception:
            log.exception("Missing required argument {}".format(exception.message))
            return {'result': 'error', 'msg': ("Missing required argument {}".format(exception.message))}

    return wrapper


def conversion_protected_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TypeError, ValueError) as exception:
            message = "Conversion failed: {}".format(exception.message)
            log.exception(message)
            return {'result': 'error', 'msg': message}

    return wrapper


def log_and_suppress_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            log.exception(exc)
            return None

    return wrapper


def get_default_stage(stages):
    """
    Gets "default" stage from collection of stages. "Default" stage is displayed if not particular stage
    was requested. Rules for getting "default" stage are as follows:
        1. If all the stages are not open - sequentially first
        2. If all the stages are closed - sequentially last
        3. If at least one opened and not closed and incomplete - first open and incomplete
        4. Otherwise - sequentially last open and not closed

    """
    stages = [stage for stage in stages if stage]
    if not stages:
        return None

    if all(not stage.is_open for stage in stages):
        return stages[0]

    if all(stage.is_closed for stage in stages):
        return stages[-1]

    available_stages = [stage for stage in stages if stage.available_now]
    try:
        return next(stage for stage in available_stages if not stage.completed)
    except StopIteration:
        pass

    return available_stages[-1]


def get_link_to_block(block):
    usage_id = block.scope_ids.usage_id
    return "/courses/{course_id}/jump_to_id/{block_id}".format(
        course_id=usage_id.course_key, block_id=usage_id.block_id
    )


def memoize_with_expiration(expires_after=None):
    """
    This memoization decorator provides lightweight caching mechanism. It is not thread-safe and contain
    no cache invalidation features except cache expiration - use only on data that are unlikely to be changed
    within single request (i.e. workgroup and user data, assigned reviews, etc.)
    """
    def decorator(func):
        cache = func.cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_list = (
                tuple([func.__name__]) + tuple(args) +
                tuple("{}:{}".format(key, value) for key, value in kwargs.iteritems())
            )
            key = make_key(key_list)
            if key not in cache or cache[key]['timestamp'] + expires_after <= datetime.now():
                result = func(*args, **kwargs)
                log.info("Updating cached value for key %s", key)
                cache[key] = {
                    'timestamp': datetime.now(),
                    'result': result
                }

            return cache[key]['result']

        return wrapper

    return decorator


def make_user_caption(user_details):
    context = {
        'id': user_details.id,
        'full_name': user_details.full_name,
        'api_link': user_details.uri
    }
    return mark_safe(loader.render_template("templates/html/user_label.html", context))


# pylint: disable=protected-access
class FieldValuesContextManager(object):
    """
    Black wizardy to workaround the fact that field values can be callable, but that callable should be
    parameterless, and we need current XBlock to get a list of values
    """
    def __init__(self, block, field_name, field_values_callback):
        self._block = block
        self._field_name = field_name
        self._callback = field_values_callback
        self._old_values_value = None

    @lazy
    def field(self):
        return self._block.fields[self._field_name]

    def __enter__(self):
        self._old_values_value = self.field.values
        self.field._values = self._callback

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.field._values = self._old_values_value
        return False

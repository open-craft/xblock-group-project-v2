""" GET, POST, DELETE, PUT requests for json client """
import logging
import urllib2 as url_access
import json
from django.conf import settings

# nice to have capitalised names for familiar GET, POST, DELETE, PUT
# pylint: disable=invalid-name

log = logging.getLogger(__name__)

JSON_HEADERS = {
    "Content-Type": "application/json",
}

if settings and hasattr(settings, "EDX_API_KEY"):
    JSON_HEADERS = {
        "Content-Type": "application/json",
        "X-Edx-Api-Key": settings.EDX_API_KEY,
    }

TIMEOUT = 20


def trace_request_information(func):
    """
    Decorator which will trace information
    """
    def make_request(*args, **kwargs):
        # log information about the request
        log_template = "Sending %s request to %s"
        log_args = [func.__name__, args[0]]

        if len(args) > 1:
            log_template += "with data %s"
            log_args.append(args[1])

        log.debug(log_template, *log_args)

        response = func(*args, **kwargs)

        log.debug("Response code: %s", response.code)

        return response

    return make_request


def json_headers():
    return JSON_HEADERS


@trace_request_information
def GET(url_path):
    """ GET request wrapper to json web server """
    url_request = url_access.Request(url=url_path, headers=json_headers())
    return url_access.urlopen(url=url_request, timeout=TIMEOUT)


@trace_request_information
def POST(url_path, data):
    """ POST request wrapper to json web server """
    url_request = url_access.Request(url=url_path, headers=json_headers())
    return url_access.urlopen(url_request, json.dumps(data), TIMEOUT)


@trace_request_information
def DELETE(url_path):
    """ DELETE request wrapper to json web server """
    opener = url_access.build_opener(url_access.HTTPHandler)
    request = url_access.Request(url=url_path, headers=json_headers())
    request.get_method = lambda: 'DELETE'
    return opener.open(request, None, TIMEOUT)


@trace_request_information
def PUT(url_path, data):
    """ PUT request wrapper to json web server """
    opener = url_access.build_opener(url_access.HTTPHandler)
    request = url_access.Request(url=url_path, headers=json_headers(), data=json.dumps(data))
    request.get_method = lambda: 'PUT'
    return opener.open(request, None, TIMEOUT)

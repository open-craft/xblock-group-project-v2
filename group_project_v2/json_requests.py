""" GET, POST, DELETE, PUT requests for json client """
import json
import logging
from urllib.request import HTTPHandler, Request, build_opener, urlopen

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
        """
        Logs information about request and response
        """
        if len(args) > 1:
            log.debug("Sending %s request to %s with data %s", func.__name__, args[0], args[1])
        else:
            log.debug("Sending %s request to %s", func.__name__, args[0])

        response = func(*args, **kwargs)

        log.debug("Response code: %s", response.code)

        return response

    return make_request


def json_headers():
    return JSON_HEADERS


@trace_request_information
def GET(url_path):
    """ GET request wrapper to json web server """
    url_request = Request(url=url_path, headers=json_headers())
    return urlopen(url=url_request, timeout=TIMEOUT)


@trace_request_information
def POST(url_path, data):
    """ POST request wrapper to json web server """
    url_request = Request(url=url_path, headers=json_headers())
    return urlopen(url_request, json.dumps(data).encode('utf-8'), TIMEOUT)


@trace_request_information
def DELETE(url_path):
    """ DELETE request wrapper to json web server """
    opener = build_opener(HTTPHandler)
    request = Request(url=url_path, headers=json_headers())
    request.get_method = lambda: 'DELETE'
    return opener.open(request, None, TIMEOUT)


@trace_request_information
def PUT(url_path, data):
    """ PUT request wrapper to json web server """
    opener = build_opener(HTTPHandler)
    request = Request(url=url_path, headers=json_headers(), data=json.dumps(data).encode('utf-8'))
    request.get_method = lambda: 'PUT'
    return opener.open(request, None, TIMEOUT)

''' GET, POST, DELETE, PUT requests for json client '''
import urllib2 as url_access
import json
from django.conf import settings

# nice to have capitalised names for familiar GET, POST, DELETE, PUT
# pylint: disable=invalid-name

JSON_HEADERS = {
    "Content-Type": "application/json",
    "X-Edx-Api-Key": settings.EDX_API_KEY,
}

TIMEOUT = 20


def json_headers():
    return JSON_HEADERS


def GET(url_path):
    print json_headers()
    ''' GET request wrapper to json web server '''
    url_request = url_access.Request(url=url_path, headers=json_headers())
    return url_access.urlopen(url=url_request, timeout=TIMEOUT)


def POST(url_path, data):
    ''' POST request wrapper to json web server '''
    url_request = url_access.Request(url=url_path, headers=json_headers())
    return url_access.urlopen(url_request, json.dumps(data), TIMEOUT)


def DELETE(url_path):
    ''' DELETE request wrapper to json web server '''
    opener = url_access.build_opener(url_access.HTTPHandler)
    request = url_access.Request(url=url_path, headers=json_headers())
    request.get_method = lambda: 'DELETE'
    return opener.open(request, None, TIMEOUT)


def PUT(url_path, data):
    ''' PUT request wrapper to json web server '''
    opener = url_access.build_opener(url_access.HTTPHandler)
    request = url_access.Request(
        url=url_path, headers=json_headers(), data=json.dumps(data))
    request.get_method = lambda: 'PUT'
    return opener.open(request, None, TIMEOUT)

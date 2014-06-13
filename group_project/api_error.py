import json
from urllib2 import HTTPError

from django.utils.translation import ugettext as _


ERROR_CODE_MESSAGES = {}

class ApiError(Exception):
    code = 1000 # 1000 represents client-side error, or unknown code
    message = _("Unknown error calling API")
    content_dictionary = {}
    http_error = None

    '''
    Exception to be thrown when the Api returns an Http error
    '''
    def __init__(self, thrown_error, error_code_messages=None):
        # store the code and
        self.http_error = thrown_error
        self.code = thrown_error.code

        self.message = thrown_error.reason

        # does the code have a known reason to be incorrect
        if error_code_messages and self.code in error_code_messages:
            self.message = error_code_messages[self.code]

        # Look in response content for specific message from api response
        try:
            self.content_dictionary = json.loads(thrown_error.read())
        except:
            self.content_dictionary = {}

        if "message" in self.content_dictionary:
            self.message = self.content_dictionary["message"]

        super(ApiError, self).__init__()

    def __str__(self):
        return "ApiError '{}' ({})".format(self.message, self.code)

def api_error_protect(func):
    '''
    Decorator which will raise an ApiError for api calls
    '''
    def call_api_method(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as he:
            api_error = ApiError(he, ERROR_CODE_MESSAGES.get(func, None))
            print "Error calling {}: {}".format(func, api_error)
    #        raise api_error
    return call_api_method

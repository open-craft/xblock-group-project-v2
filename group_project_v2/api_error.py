import logging
import json
from urllib.error import HTTPError  # pylint: disable=F0401
from future import standard_library
standard_library.install_aliases()


from group_project_v2.utils import gettext as _


log = logging.getLogger(__name__)

ERROR_CODE_MESSAGES = {}


class ApiError(Exception):
    """
    Exception to be thrown when the Api returns an Http error
    """
    code = 1000  # 1000 represents client-side error, or unknown code
    message = _("Unknown error calling API")
    content_dictionary = {}
    http_error = None

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
        except Exception:  # pylint: disable=broad-except
            self.content_dictionary = {}

        if "message" in self.content_dictionary:
            self.message = self.content_dictionary["message"]

        super(ApiError, self).__init__()

    def __str__(self):
        return "ApiError '{}' ({})".format(self.message, self.code)


def api_error_protect(func):
    """
    Decorator which will raise an ApiError for api calls
    """

    def call_api_method(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as http_error:
            api_error = ApiError(http_error, ERROR_CODE_MESSAGES.get(func.__name__, None))
            log.exception("Error calling %s: %s", func.__name__, api_error)
            raise api_error  # pylint: disable=raise-missing-from

    return call_api_method

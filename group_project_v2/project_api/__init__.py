''' API calls with respect group projects'''

from django.conf import settings
from lazy.lazy import lazy

from group_project_v2.project_api.api_implementation import TypedProjectAPI

# Looks like it's an issue, but technically it's not; this code runs in LMS, so 127.0.0.1 is always correct
# location for API server, as it's basically executed in a neighbour thread/process/whatever.
API_SERVER = "http://127.0.0.1:8000"
if hasattr(settings, 'API_LOOPBACK_ADDRESS'):
    API_SERVER = settings.API_LOOPBACK_ADDRESS


class ProjectAPIXBlockMixin(object):
    _project_api = None

    @lazy
    def project_api(self):
        # project_api instance needs to be static to allow workgroup caching in WorkgroupAwareXBlockMixin
        if ProjectAPIXBlockMixin._project_api is None:
            author_mode = getattr(self.runtime, 'is_author_mode', False)
            ProjectAPIXBlockMixin._project_api = TypedProjectAPI(API_SERVER, author_mode)

        return ProjectAPIXBlockMixin._project_api

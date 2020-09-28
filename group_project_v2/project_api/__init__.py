""" Project API client """
from builtins import object
from django.conf import settings

from group_project_v2.project_api.api_implementation import TypedProjectAPI

# Looks like it's an issue, but technically it's not; this code runs in LMS, so 127.0.0.1 is always correct
# location for API server, as it's basically executed in a neighbour thread/process/whatever.
API_SERVER = getattr(settings, 'API_LOOPBACK_ADDRESS', "http://127.0.0.1:8000")


class ProjectAPIXBlockMixin(object):
    _project_api = None

    @property
    def project_api(self):
        """
        :rtype: TypedProjectAPI
        """
        # project_api instance needs to be static to allow workgroup caching in WorkgroupAwareXBlockMixin
        if ProjectAPIXBlockMixin._project_api is None:
            author_mode = getattr(self.runtime, 'is_author_mode', False)
            ProjectAPIXBlockMixin._project_api = TypedProjectAPI(API_SERVER, author_mode)

        return ProjectAPIXBlockMixin._project_api

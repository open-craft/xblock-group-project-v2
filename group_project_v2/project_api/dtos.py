""" Contains DTOs used in Typed API. DTOs mostly follow structure of API responses """
from group_project_v2.utils import make_user_caption


# pylint:disable=too-many-instance-attributes
class UserDetails(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.email = kwargs.get('email', None)
        self.username = kwargs.get('username', None)
        self.url = kwargs.get('uri', None)
        self.first_name = kwargs.get('first_name', None)
        self.last_name = kwargs.get('last_name', None)
        self._full_name = kwargs.get('full_name', None)
        self.gender = kwargs.get('gender', None)
        self.avatar_url = kwargs.get('avatar_url', None)
        self.city = kwargs.get('city', None)
        self.country = kwargs.get('country', None)
        self.is_active = kwargs.get('is_active', None)
        self.level_of_education = kwargs.get('level_of_education', None)
        self.organization = kwargs.get('organization', None)

    @property
    def full_name(self):
        if self._full_name:
            return self._full_name
        return u" ".join([unicode(part) for part in (self.first_name, self.last_name) if part is not None])

    @property
    def user_label(self):
        return make_user_caption(self)


class ProjectDetails(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.url = kwargs.get('url')
        self.created = kwargs.get('created')
        self.modified = kwargs.get('modified')
        self.course_id = kwargs.get('course_id')
        self.content_id = kwargs.get('content_id')
        self.organization = kwargs.get('organization')
        self.workgroups = kwargs.get('workgroups')


class WorkgroupDetails(object):
    """
    :type users: list[ReducedUserDetails]
    """
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.url = kwargs.get('url')
        self.created = kwargs.get('created')
        self.modified = kwargs.get('modified')
        self.name = kwargs.get('name')
        self.project = kwargs.get('project')
        self.groups = kwargs.get('groups')
        self.workgroups = kwargs.get('workgroups')
        users = kwargs.get('users')
        self.users = []
        if users:
            self.users = [ReducedUserDetails(**user_detail) for user_detail in users]
        self.submissions = kwargs.get('submissions')
        self.workgroup_reviews = kwargs.get('workgroup_reviews')
        self.peer_reviews = kwargs.get('peer_reviews')


class ReducedUserDetails(object):
    """ User data embedded in a workgroup detail response """
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.url = kwargs.get('url')
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')


class CompletionDetails(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.course_id = kwargs.get('course_id')
        self.content_id = kwargs.get('content_id')
        self.stage = kwargs.get('stage')
        self.created = kwargs.get('created')
        self.modified = kwargs.get('modified')

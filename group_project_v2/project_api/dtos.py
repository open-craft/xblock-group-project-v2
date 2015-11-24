from group_project_v2.utils import make_user_caption


# pylint:disable=too-many-instance-attributes
class UserDetails(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.email = kwargs.get('email', None)
        self.username = kwargs.get('username', None)
        self.uri = kwargs.get('uri', None)
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
        parts = [self.first_name, self.last_name]
        return u" ".join([unicode(part) for part in parts if part is not None])

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
        self.workgroup_ids = kwargs.get('workgroups')



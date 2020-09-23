from builtins import str
from builtins import next
from builtins import object
import functools
import logging
import os
import itertools

from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import BlockUsageLocator
from web_fragments.fragment import Fragment
from xblock.completable import XBlockCompletionMode
from xblockutils.studio_editable import (
    StudioContainerWithNestedXBlocksMixin, StudioContainerXBlockMixin, StudioEditableXBlockMixin
)

from group_project_v2.api_error import ApiError
from group_project_v2.project_api import ProjectAPIXBlockMixin
from group_project_v2.project_api.dtos import WorkgroupDetails
from group_project_v2.utils import (
    MUST_BE_OVERRIDDEN, NO_EDITABLE_SETTINGS, Constants, GroupworkAccessDeniedError,
    loader, groupwork_protected_view, add_resource
)

log = logging.getLogger(__name__)


class ChildrenNavigationXBlockMixin(object):
    @lazy
    def _children(self):
        children = (self.runtime.get_block(child_id) for child_id in self.children)
        return [child for child in children if child is not None]

    @staticmethod
    def get_child_category(child):
        field_candidates = ('category', 'plugin_name')
        try:
            return next(getattr(child, field) for field in field_candidates if hasattr(child, field))
        except StopIteration:
            return None

    @staticmethod
    def get_child_id_block_type(child_id):
        try:
            return child_id.block_type
        except AttributeError:  # workbench support
            return child_id.split(".")[1]

    def get_children_by_category(self, *child_categories):
        return [child for child in self._children if self.get_child_category(child) in child_categories]

    def get_child_of_category(self, child_category):
        try:
            return next(child for child in self._children if self.get_child_category(child) == child_category)
        except StopIteration:
            return None

    def has_child_of_category(self, child_category):
        return any(self.get_child_id_block_type(child) == child_category for child in self.children)

    @staticmethod
    def get_block_id_from_string(block_id_string):
        if not block_id_string:
            return None
        try:
            return BlockUsageLocator.from_string(block_id_string)
        except InvalidKeyError:  # workbench support
            return block_id_string

    def _render_children(self, view, children_context, children=None):
        children_to_render = children if children is not None else self._children
        results = [child.render(view, children_context) for child in children_to_render]

        return results


class CourseAwareXBlockMixin(object):
    @property
    def course_id(self):
        raw_course_id = getattr(self.runtime, 'course_id', 'all')
        return str(raw_course_id)


class UserAwareXBlockMixin(ProjectAPIXBlockMixin):
    TA_REVIEW_KEY = "TA_REVIEW_WORKGROUP"

    @lazy
    def anonymous_student_id(self):
        try:
            return self.runtime.anonymous_student_id
        except AttributeError:
            log.warning("Runtime does not have anonymous_student_id attribute - trying user_id")
            return self.runtime.user_id

    @lazy
    # pylint: disable=broad-except
    def user_id(self):
        try:
            return int(self.real_user_id(self.anonymous_student_id))
        except Exception as exc:
            # Suppressing logs when access through studio
            if not getattr(self.runtime, 'is_author_mode', False):
                log.exception(exc)
            try:
                return int(self.runtime.user_id)
            except Exception as exc:
                log.exception(exc)
                return None

    @lazy
    def user_preferences(self):
        return self.project_api.get_user_preferences(self.user_id)

    @property
    def is_admin_grader(self):
        return UserAwareXBlockMixin.TA_REVIEW_KEY in self.user_preferences

    _known_real_user_ids = {}

    def real_user_id(self, anonymous_student_id):
        if anonymous_student_id not in self._known_real_user_ids:
            if hasattr(self.runtime, 'get_real_user'):
                self._known_real_user_ids[anonymous_student_id] = self.runtime.get_real_user(anonymous_student_id).id
            else:
                self._known_real_user_ids[anonymous_student_id] = anonymous_student_id
        return self._known_real_user_ids[anonymous_student_id]


class SettingsMixin(object):

    def _get_setting(self, setting, default):
        result = default
        settings_service = self.runtime.service(self, "settings")
        if settings_service:
            xblock_settings = settings_service.get_settings_bucket(self)
            if xblock_settings and setting in xblock_settings:
                result = xblock_settings[setting]
        return result


class AuthXBlockMixin(SettingsMixin, ProjectAPIXBlockMixin, CourseAwareXBlockMixin):

    DEFAULT_TA_ROLE = ("assistant", )

    ACCESS_DASHBOARD_ROLE_PERMS_KEY = "access_dashboard_groups"
    ACCESS_DASHBOARD_FOR_ALL_ORGS_PERMS_KEY = "access_dashboard_for_all_orgs_groups"
    ACCESS_DASHBOARD_TA_PERMS_KEY = "access_dashboard_ta_groups"
    COURSE_ACCESS_TA_ROLES_KEY = "ta_roles"

    @property
    def see_dashboard_ta_perms(self):
        """
        :return: Returns a set of group names, if user is a member of any
                 group in the set, he can access the dashboard for a course
                 if he has a TA role for that particular course.
                 (Essentially he needs to pass ``check_ta_access`` test.)

                 Additionally he will see this dashboard filtered so he
                 sees groups with students from the organisation he
                 belongs to.

        :rtype: set[str]
        """
        return set(self._get_setting(self.ACCESS_DASHBOARD_TA_PERMS_KEY, []))

    @property
    def see_dashboard_role_perms(self):
        """
        :return: Returns a set of group names, user needs to be a member of
                 any group from this list to access dashboard.

                 Additionally he will see this dashboard filtered so he
                 sees groups with students from the organisation he
                 belongs to.
        :rtype: set[str]
        """
        return set(self._get_setting(self.ACCESS_DASHBOARD_ROLE_PERMS_KEY, []))

    @property
    def see_dashboard_for_all_orgs_perms(self):
        """
        :return: Returns a set of group names, user needs to be a member of
                 any group from this list to access dashboard.
                 Members of these group will see dashboard with users
                 from all organizations.
        :rtype: set[str]
        """
        return set(self._get_setting(self.ACCESS_DASHBOARD_FOR_ALL_ORGS_PERMS_KEY, []))

    @property
    def ta_roles(self):
        """

        .. note:

            This returns different thing than self.see_dashboard_for_all_orgs
            this returns a **course** role, and rest contains a user group.

        :return: A list of course roles, if a user has any role from this list for a
                 particular course, he is considered to be a TA for that course.
        :rtype: set[str]
        """
        return set(self._get_setting(self.COURSE_ACCESS_TA_ROLES_KEY, self.DEFAULT_TA_ROLE))

    def can_access_dashboard(self, user_id):
        """
        :param user_id:
        :return: True if user can access dashboard.
        :rtype: bool
        """
        user_groups = self._user_groups(user_id)

        # These users can access dashboard for every course
        if bool(user_groups & self._access_dashboard_roles):
            return True

        # These users can access dashboard only if they are TA
        if bool(user_groups & self.see_dashboard_ta_perms):
            return self.is_user_ta(user_id, self.course_id)

        return False

    @staticmethod
    def check_dashboard_access_for_current_user(func):

        @functools.wraps(func)
        def check_dashboard_access_wrapper(self, *args, **kwargs):
            if not self.can_access_dashboard(self.user_id):
                raise GroupworkAccessDeniedError("User can't access dashboard")
            return func(self, *args, **kwargs)

        return check_dashboard_access_wrapper

    def is_user_ta(self, user_id, course_id):
        """
        :return: True if user is a TA for a gven course
        :rtype: bool
        """

        granted_roles = self.project_api.get_user_roles_for_course(user_id, course_id)
        allowed_roles = set(self.ta_roles)
        return bool(allowed_roles & granted_roles)

    def check_ta_access(self, user_id, course_id):
        """
        :return: None
        :raise GroupworkAccessDeniedError: If user can't access a groupwork item
        if he is not part of the team.
        """
        if not self.is_user_ta(user_id, course_id):
            raise GroupworkAccessDeniedError("User can't access this group work")

    def get_organization_filter_for_user(self, user_id, additional_filter=None):
        """
        :param Iterable[int] additional_filter:
            Iterable of organization ids that are filtered additionally.
        :return: Returns object that can be used if user_id has access to
                 an organization. This callable returns bool an expects to be
                 called with organization id.
        :rtype: Callable[[int], bool]
        """
        if self._can_user_access_all_orgs(user_id):
            allowed_org_ids = None
        else:
            allowed_orgs = self.project_api.get_user_organizations(user_id)
            allowed_org_ids = set(org['id'] for org in allowed_orgs)
        return self.OrganizationFilter(self.project_api, user_id, allowed_org_ids, additional_filter)

    class OrganizationFilter(object):

        """
        A class that checks whether an user can access an organization.

        Contains two sets: one with organizations user has access to, and second
        with organizations that user has explicitily filtered for.

        Value None means "all organizations" --- since there can be a large
        number of organizations, we avoid keeping "all organizations" that way.
        """

        def __init__(self, project_api, user_id, allowed_org_ids, filter_org_ids=None):
            """
            :param TypedProjectApi project_api:
            :param user_id:
            :param set[int] allowed_org_ids:
            :param set[int] filter_org_ids:
            """
            self.project_api = project_api
            self.user_id = user_id
            self.filter_org_ids = set(filter_org_ids) if filter_org_ids is not None else None
            """
            :type: set[int] or None
            """  # pylint: disable=pointless-string-statement
            self.allowed_org_ids = set(allowed_org_ids) if allowed_org_ids is not None else None
            """
            :type: set[int] or None
            """  # pylint: disable=pointless-string-statement

        def can_access_other_user(self, user_id):
            """
            :param user_id:
            :return: True if this user can access user with id of ``user_id``.
                     This user is the user for which this ``OrganizationFilter``
                     was created (see: self.user_id).
            :rtype bool:
            """
            orgs = self.project_api.get_user_organizations(user_id)
            return any(self.can_access_other_organization(org['id']) for org in orgs)

        def can_access_other_organization(self, organization_id):
            """
            :param organization_id:
            :return: True if user can see this org
            :rtype bool:
            """
            if self.allowed_org_ids is not None and organization_id not in self.allowed_org_ids:
                return False
            if self.filter_org_ids is not None and organization_id not in self.filter_org_ids:
                return False
            return True

    def _user_groups(self, user_id):
        """
        :param user_id:
        :return: A set containing a name of each group user belongs to.
        :rtype: set[str]
        """
        return set(group.name for group in self.project_api.get_user_permissions(user_id))

    def _can_user_access_all_orgs(self, user_id):
        """
        :param user_id:
        :return: True if user can access all organizations
        :rtype: bool
        """
        return bool(set(self.see_dashboard_for_all_orgs_perms) & set(self._user_groups(user_id)))

    @property
    def _access_dashboard_roles(self):
        """
        :return: Set containing all names of groups allowing user to
                 access the dashboard.
        :rtype: set[str]
        """
        return set(itertools.chain(self.see_dashboard_role_perms, self.see_dashboard_for_all_orgs_perms))


class WorkgroupAwareXBlockMixin(AuthXBlockMixin, UserAwareXBlockMixin, CourseAwareXBlockMixin):
    """
    Gets current user workgroup, respecting TA review
    """
    FALLBACK_WORKGROUP = WorkgroupDetails(id=0, users=[])

    @property
    def group_id(self):
        """
        :rtype: int
        """
        return self.workgroup.id

    @property
    def is_group_member(self):
        """
        :rtype: bool
        """
        return self.user_id in [u.id for u in self.workgroup.users]

    @property
    def workgroup(self):
        """
        :rtype: WorkgroupDetails
        """
        try:
            user_prefs = self.user_preferences
            if UserAwareXBlockMixin.TA_REVIEW_KEY in user_prefs:
                self.check_ta_access(self.user_id, self.course_id)
                return self.project_api.get_workgroup_by_id(
                    user_prefs[UserAwareXBlockMixin.TA_REVIEW_KEY]
                )
            workgroup = self.project_api.get_user_workgroup_for_course(
                self.user_id, self.course_id
            )
            if workgroup is None:
                return self.FALLBACK_WORKGROUP
            return workgroup
        # pylint: disable=try-except-raise
        except GroupworkAccessDeniedError:
            raise
        except ApiError as exception:
            log.exception(exception)
            return self.FALLBACK_WORKGROUP


class XBlockWithComponentsMixin(StudioContainerWithNestedXBlocksMixin):
    CHILD_PREVIEW_TEMPLATE = "templates/html/default_preview_view.html"

    @property
    def loader(self):
        return loader

    @groupwork_protected_view
    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = super(XBlockWithComponentsMixin, self).author_edit_view(context)
        add_resource(self, 'css', 'public/css/group_project.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_edit.css', fragment)
        return fragment

    @groupwork_protected_view
    def author_preview_view(self, context):
        fragment = super(XBlockWithComponentsMixin, self).author_preview_view(context)
        add_resource(self, 'css', 'public/css/group_project.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_preview.css', fragment)
        return fragment


class XBlockWithUrlNameDisplayMixin(object):
    @property
    def url_name(self):
        """
        Get the url_name for this block. In Studio/LMS it is provided by a mixin, so we just
        defer to super(). In the workbench or any other platform, we use the usage_id.
        """
        try:
            return super(XBlockWithUrlNameDisplayMixin, self).url_name
        except AttributeError:
            return str(self.scope_ids.usage_id)

    def get_url_name_fragment(self, caption):
        fragment = Fragment()
        fragment.add_content(loader.render_template(
            "templates/html/url_name.html",
            {'url_name': self.url_name, 'caption': caption}
        ))
        return fragment


class AdminAccessControlXBlockMixin(object):
    @property
    def allow_admin_grader_access(self):  # pylint: disable=no-self-use
        return False

    @property
    def available_to_current_user(self):
        return self.allow_admin_grader_access or not self.is_admin_grader


class NoStudioEditableSettingsMixin(object):
    def studio_view(self, _context):  # pylint: disable=no-self-use
        fragment = Fragment()
        fragment.add_content(NO_EDITABLE_SETTINGS)
        return fragment


class DashboardXBlockMixin(object):
    """ Mixin for an XBlock that has dashboard views """
    DASHBOARD_PROGRAM_ID_KEY = "DASHBOARD_PROGRAM_ID"

    def dashboard_view(self, context):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def dashboard_detail_view(self, context):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)


class DashboardRootXBlockMixin(AuthXBlockMixin, UserAwareXBlockMixin):
    """
    Mixin for an XBlock that can act as a root XBlock for dashboard view.
    Dashboard root XBlock is responsible for injecting workgroups and students into the view context
    """
    def _add_students_and_workgroups_to_context(self, context):
        """
        :param dict context: XBlock view context
        :rtype: None
        """
        workgroups, students = self.get_workgroups_and_students()

        context[Constants.TARGET_STUDENTS] = list(students)
        context[Constants.TARGET_WORKGROUPS] = list(workgroups)
        context[Constants.FILTERED_STUDENTS] = set()

        # If not None students not belonging to organization represented by given id will be filtered out
        filter_by_organization_id = context.get(Constants.CURRENT_CLIENT_FILTER_ID_PARAMETER_NAME, None)

        if filter_by_organization_id is None:
            filter_by_organization_id = None
        else:
            filter_by_organization_id = [filter_by_organization_id]

        org_filter = self.get_organization_filter_for_user(self.user_id, filter_by_organization_id)

        filtered_students = set()

        for workgroup in workgroups:
            for user in workgroup.users:
                if not org_filter.can_access_other_user(user.id):
                    filtered_students.add(user.id)

        context[Constants.FILTERED_STUDENTS] = filtered_students

    def get_workgroups_and_students(self):
        return list(self.workgroups), list(self.all_users_in_workgroups)

    @property
    def project_details(self):
        """
        Gets ProjectDetails for current block
        :rtype: group_project_v2.project_api.dtos.ProjectDetails
        """
        return self.project_api.get_project_by_content_id(self.course_id, self.content_id)

    @property
    def workgroups(self):
        """
        :rtype: collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails]
        """
        return (
            self.project_api.get_workgroup_by_id(workgroup_id)
            for workgroup_id in self.project_details.workgroups
        )

    @property
    def all_users_in_workgroups(self):
        """
        :rtype: collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails]
        """
        return itertools.chain.from_iterable(workgroup.users for workgroup in self.workgroups)


class TemplateManagerMixin(object):
    BASE_TEMPLATE_LOCATION = "templates/html"
    template_location = None

    def render_template(self, template, context, template_suffix=".html"):
        template_path = os.path.join(self.BASE_TEMPLATE_LOCATION, self.template_location, template + template_suffix)
        return loader.render_template(template_path, context)


class CompletionMixin(object):
    completion_mode = XBlockCompletionMode.EXCLUDED


class CommonMixinCollection(
        ChildrenNavigationXBlockMixin, XBlockWithComponentsMixin,
        StudioEditableXBlockMixin, StudioContainerXBlockMixin,
        WorkgroupAwareXBlockMixin, TemplateManagerMixin, SettingsMixin,
        CompletionMixin,
):
    block_settings_key = 'group_project_v2'

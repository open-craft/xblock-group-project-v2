import logging
from datetime import timedelta
import os
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import BlockUsageLocator
from xblock.fragment import Fragment

from group_project_v2.api_error import ApiError
from group_project_v2.project_api import ProjectAPIXBlockMixin
from group_project_v2.utils import (
    OutsiderDisallowedError, ALLOWED_OUTSIDER_ROLES,
    loader, outsider_disallowed_protected_view, NO_EDITABLE_SETTINGS, memoize_with_expiration, add_resource,
    MUST_BE_OVERRIDDEN)
from xblockutils.studio_editable import (
    StudioContainerWithNestedXBlocksMixin, StudioContainerXBlockMixin, StudioEditableXBlockMixin
)

log = logging.getLogger(__name__)


class ChildrenNavigationXBlockMixin(object):
    @lazy
    def _children(self):
        children = (self.runtime.get_block(child_id) for child_id in self.children)
        return [child for child in children if child is not None]

    @staticmethod
    def get_child_category(child):  # pylint: disable=no-self-use
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

    def get_block_id_from_string(self, block_id_string):  # pylint: disable=no-self-use
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
        return unicode(raw_course_id)


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
            log.exception(exc)
            try:
                return int(self.runtime.user_id)
            except Exception as exc:
                log.exception(exc)
                return None

    @lazy
    def user_preferences(self):
        return self._user_preferences(self.project_api, self.user_id)

    @staticmethod
    @memoize_with_expiration(expires_after=timedelta(seconds=5))
    def _user_preferences(project_api, user_id):
        return project_api.get_user_preferences(user_id)

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


class WorkgroupAwareXBlockMixin(UserAwareXBlockMixin, CourseAwareXBlockMixin):
    """
    Gets current user workgroup, respecting TA review
    """
    FALLBACK_WORKGROUP = {"id": "0", "users": []}

    @property
    def group_id(self):
        return self.workgroup['id']

    @property
    def is_group_member(self):
        return self.user_id in [u["id"] for u in self.workgroup["users"]]

    @staticmethod
    def _confirm_outsider_allowed(project_api, user_id, course_id):
        granted_roles = {r["role"] for r in project_api.get_user_roles_for_course(user_id, course_id)}
        allowed_roles = set(ALLOWED_OUTSIDER_ROLES)

        if not (allowed_roles & granted_roles):
            raise OutsiderDisallowedError("User does not have an allowed role")

    @property
    def workgroup(self):
        workgroup = self._get_workgroup(self.project_api, self.user_id, self.course_id)
        return workgroup if workgroup else self.FALLBACK_WORKGROUP

    @staticmethod
    @memoize_with_expiration(expires_after=timedelta(seconds=5))
    def _get_workgroup(project_api, user_id, course_id):
        try:
            user_prefs = UserAwareXBlockMixin._user_preferences(project_api, user_id)

            if UserAwareXBlockMixin.TA_REVIEW_KEY in user_prefs:
                WorkgroupAwareXBlockMixin._confirm_outsider_allowed(project_api, user_id, course_id)
                result = project_api.get_workgroup_by_id(user_prefs[UserAwareXBlockMixin.TA_REVIEW_KEY])
            else:
                result = project_api.get_user_workgroup_for_course(user_id, course_id)
        except OutsiderDisallowedError:
            raise
        except ApiError as exception:
            log.exception(exception)
            result = None

        return result


class XBlockWithComponentsMixin(StudioContainerWithNestedXBlocksMixin):
    CHILD_PREVIEW_TEMPLATE = "templates/html/default_preview_view.html"

    @property
    def loader(self):
        return loader

    @outsider_disallowed_protected_view
    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = super(XBlockWithComponentsMixin, self).author_edit_view(context)
        add_resource(self, 'css', 'public/css/group_project.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_edit.css', fragment)
        return fragment

    @outsider_disallowed_protected_view
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
            return unicode(self.scope_ids.usage_id)

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
    def studio_view(self, context):  # pylint: disable=unused-argument, no-self-use
        fragment = Fragment()
        fragment.add_content(NO_EDITABLE_SETTINGS)
        return fragment


class DashboardMixin(object):
    def dashboard_view(self, context):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)


class TemplateManagerMixin(object):
    BASE_TEMPLATE_LOCATION = "templates/html"
    template_location = None

    def render_template(self, template, context, template_suffix=".html"):
        template_path = os.path.join(self.BASE_TEMPLATE_LOCATION, self.template_location, template + template_suffix)
        return loader.render_template(template_path, context)


class CommonMixinCollection(
    ChildrenNavigationXBlockMixin, XBlockWithComponentsMixin,
    StudioEditableXBlockMixin, StudioContainerXBlockMixin,
    WorkgroupAwareXBlockMixin, TemplateManagerMixin, DashboardMixin
):
    def dashboard_view(self, context):  # just to make pylint and other static analyzers happy
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

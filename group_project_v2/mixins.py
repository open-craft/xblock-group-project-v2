import logging
from datetime import timedelta
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import BlockUsageLocator
from xblock.exceptions import NoSuchViewError
from xblock.fragment import Fragment

from group_project_v2.api_error import ApiError
from group_project_v2.project_api import ProjectAPIXBlockMixin
from group_project_v2.utils import (
    OutsiderDisallowedError, ALLOWED_OUTSIDER_ROLES,
    loader, outsider_disallowed_protected_view, NO_EDITABLE_SETTINGS, memoize_with_expiration
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

    def get_children_by_category(self, *child_categories):
        return [child for child in self._children if self.get_child_category(child) in child_categories]

    def get_child_of_category(self, child_category):
        try:
            return next(child for child in self._children if self.get_child_category(child) == child_category)
        except StopIteration:
            return None

    def has_child_of_category(self, child_category):
        return any(child.block_type == child_category for child in self.children)

    def get_block_by_id(self, block_id):
        try:
            usage_id = BlockUsageLocator.from_string(block_id)
        except InvalidKeyError:
            usage_id = block_id

        return self.runtime.get_block(usage_id)


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


class NestedXBlockSpec(object):
    def __init__(self, block, single_instance=False, disabled=False, disabled_reason=None):
        self._block = block
        self._single_instance = single_instance
        self._disabled = disabled
        self._disabled_reason = disabled_reason

    @property
    def category(self):
        return self._block.CATEGORY

    @property
    def label(self):
        return self._block.STUDIO_LABEL

    @property
    def single_instance(self):
        return self._single_instance

    @property
    def disabled(self):
        return self._disabled

    @property
    def disabled_reason(self):
        return self._disabled_reason


class XBlockWithComponentsMixin(object):
    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return []

    def get_nested_blocks_spec(self):
        return [
            block_spec if isinstance(block_spec, NestedXBlockSpec) else NestedXBlockSpec(block_spec)
            for block_spec in self.allowed_nested_blocks
        ]

    @outsider_disallowed_protected_view
    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()

        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(
            loader.render_template('templates/html/add_buttons.html', {'child_blocks': self.get_nested_blocks_spec()})
        )
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project.css'))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/xblock_with_components_edit.js'))
        fragment.initialize_js('XBlockWithComponentsEdit')
        return fragment

    @outsider_disallowed_protected_view
    def author_preview_view(self, context):
        children_contents = []

        fragment = Fragment()
        for child in self._children:
            child_fragment = self._render_child_fragment(child, context, 'preview_view')
            fragment.add_frag_resources(child_fragment)
            children_contents.append(child_fragment.content)

        render_context = {
            'block': self,
            'children_contents': children_contents
        }
        render_context.update(context)
        fragment.add_content(loader.render_template("templates/html/default_preview_view.html", render_context))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project.css'))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_preview.css'))
        return fragment

    def _render_child_fragment(self, child, context, view='student_view'):
        try:
            child_fragment = child.render(view, context)
        except NoSuchViewError:
            if child.scope_ids.block_type == 'html' and getattr(self.runtime, 'is_author_mode', False):
                # html block doesn't support preview_view, and if we use student_view Studio will wrap
                # it in HTML that we don't want in the preview. So just render its HTML directly:
                child_fragment = Fragment(child.data)
            else:
                child_fragment = child.render('student_view', context)

        return child_fragment


class XBlockWithPreviewMixin(object):
    def preview_view(self, context):
        view_to_render = 'author_view' if hasattr(self, 'author_view') else 'student_view'
        renderer = getattr(self, view_to_render)
        return renderer(context)


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

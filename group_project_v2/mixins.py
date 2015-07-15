import logging
from lazy.lazy import lazy
from xblock.exceptions import NoSuchViewError
from xblock.fragment import Fragment

from group_project_v2.api_error import ApiError
from group_project_v2.project_api import project_api
from group_project_v2.utils import OutsiderDisallowedError, ALLOWED_OUTSIDER_ROLES, loader

log = logging.getLogger(__name__)


class ChildrenNavigationXBlockMixin(object):
    @lazy
    def _children(self):
        return [self.runtime.get_block(child_id) for child_id in self.children]

    def _get_children_by_category(self, child_category):
        return [child for child in self._children if child.category == child_category]


class CourseAwareXBlockMixin(object):
    @property
    def course_id(self):
        raw_course_id = getattr(self.runtime, 'course_id', 'all')
        try:
            return unicode(raw_course_id)
        except Exception:    # pylint: disable=broad-except
            return raw_course_id


class UserAwareXBlockMixin(object):
    @lazy
    def anonymous_student_id(self):
        try:
            return self.runtime.anonymous_student_id
        except AttributeError:
            log.exception("Runtime does not have anonymous_student_id attribute - trying user_id")
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

    _known_real_user_ids = {}

    def real_user_id(self, anonymous_student_id):
        if anonymous_student_id not in self._known_real_user_ids:
            try:
                self._known_real_user_ids[anonymous_student_id] = self.runtime.get_real_user(anonymous_student_id).id
            except AttributeError:
                # workbench support
                self._known_real_user_ids[anonymous_student_id] = anonymous_student_id
        return self._known_real_user_ids[anonymous_student_id]


class WorkgroupAwareXBlockMixin(object):
    def _confirm_outsider_allowed(self):
        granted_roles = [r["role"] for r in project_api.get_user_roles_for_course(self.user_id, self.course_id)]
        for allowed_role in ALLOWED_OUTSIDER_ROLES:
            if allowed_role in granted_roles:
                return True

        raise OutsiderDisallowedError("User does not have an allowed role")

    @lazy
    def workgroup(self):
        fallback_result = {
            "id": "0",
            "users": [],
        }

        try:
            user_prefs = project_api.get_user_preferences(self.user_id)

            if "TA_REVIEW_WORKGROUP" in user_prefs:
                self._confirm_outsider_allowed()
                result = project_api.get_workgroup_by_id(user_prefs["TA_REVIEW_WORKGROUP"])
            else:
                result = project_api.get_user_workgroup_for_course(self.user_id, self.course_id)
        except OutsiderDisallowedError:
            raise
        except ApiError as exception:
            log.exception(exception)
            result = None

        return result if result is not None else fallback_result


class XBlockWithComponentsMixin(object):
    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return None

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()

        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(
            loader.render_template('templates/html/add_buttons.html', {'child_blocks': self.allowed_nested_blocks})
        )
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        return fragment

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
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
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

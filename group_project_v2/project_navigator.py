"""
This module contains Project Navigator XBlock and it's children view XBlocks
"""
import logging
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from xblock.core import XBlock
from xblock.exceptions import NoSuchUsage
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.studio_editable import StudioContainerXBlockMixin, StudioEditableXBlockMixin
from group_project_v2.mixins import (
    XBlockWithComponentsMixin, XBlockWithPreviewMixin, ChildrenNavigationXBlockMixin,
    XBlockWithUrlNameDisplayMixin, AdminAccessControlXBlockMixin, NoStudioEditableSettingsMixin
)

from group_project_v2.utils import loader, gettext as _

log = logging.getLogger(__name__)


class ViewTypes(object):
    """
    View type constants
    """
    NAVIGATION = 'navigation'
    RESOURCES = 'resources'
    SUBMISSIONS = 'submissions'
    ASK_TA = 'ask-ta'


class GroupProjectNavigatorXBlock(
    ChildrenNavigationXBlockMixin, XBlockWithComponentsMixin, XBlockWithPreviewMixin,
    NoStudioEditableSettingsMixin, StudioContainerXBlockMixin, XBlock
):
    """
    XBlock that provides basic layout and switching between children XBlocks (views)
    Should only be added as a child to GroupProjectXBlock
    """
    CATEGORY = "gp-v2-navigator"
    STUDIO_LABEL = _(u"Group Project Navigator")
    INITIAL_VIEW = ViewTypes.NAVIGATION

    display_name_with_default = _(u"Group Project Navigator")

    editable = False
    has_score = False
    has_children = True

    @lazy
    def group_project(self):
        """
        Reference to parent XBlock
        """
        return self.get_parent()

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return [NavigationViewXBlock, ResourcesViewXBlock, SubmissionsViewXBlock, AskTAViewXBlock]

    def _get_activated_view_type(self, activate_block_id):
        try:
            if activate_block_id:
                block = self.get_block_by_id(activate_block_id)
                if self.get_child_category(block) in PROJECT_NAVIGATOR_VIEW_TYPES:
                    return block.type
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        return ViewTypes.NAVIGATION

    def student_view(self, context):
        """
        Student view
        """
        fragment = Fragment()
        children_items = []
        for child_id in self.children:
            view = self.runtime.get_block(child_id)
            if not view.available_to_current_user:
                continue
            child_fragment = view.render('student_view', context)

            item = {
                'id': str(child_id).replace("/", ";_"),
                'type': view.type,
                'content': child_fragment.content,
            }

            fragment.add_frag_resources(child_fragment)

            if not view.skip_selector:
                child_selector_fragment = view.selector_view(context)
                item['selector'] = child_selector_fragment.content
                fragment.add_frag_resources(child_selector_fragment)
            else:
                item['selector'] = ''

            children_items.append(item)

        js_parameters = {
            'selected_view': self._get_activated_view_type(context.get('activate_block_id', None))
        }

        fragment.add_content(
            loader.render_template(
                'templates/html/project_navigator/project_navigator.html',
                {'children': children_items}
            )
        )
        fragment.add_css_url(self.runtime.local_resource_url(
            self, 'public/css/project_navigator/project_navigator.css'
        ))
        fragment.add_javascript_url(self.runtime.local_resource_url(
            self, 'public/js/project_navigator/project_navigator.js'
        ))
        fragment.initialize_js("GroupProjectNavigatorBlock", js_parameters)

        return fragment

    def author_preview_view(self, context):  # pylint: disable=unused-argument, no-self-use
        fragment = Fragment()
        children_contents = []
        for child in self._children:
            child_fragment = child.render('preview_view', context)
            fragment.add_frag_resources(child_fragment)
            children_contents.append(child_fragment.content)

        fragment.add_content(loader.render_template(
            "templates/html/project_navigator/project_navigator_author_view.html",
            {'navigator': self, 'children_contents': children_contents}
        ))
        fragment.add_css_url(self.runtime.local_resource_url(
            self, 'public/css/project_navigator/project_navigator.css'
        ))
        return fragment

    def validate(self):
        validation = super(GroupProjectNavigatorXBlock, self).validate()

        if not self.has_child_of_category(NavigationViewXBlock.CATEGORY):
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Project Navigator must contain Navigation view")
            ))

        return validation


class ProjectNavigatorViewXBlockBase(
    XBlock, XBlockWithPreviewMixin, StudioEditableXBlockMixin, XBlockWithUrlNameDisplayMixin,
    AdminAccessControlXBlockMixin
):
    """
    Base class for Project Navigator children XBlocks (views)
    """
    type = None
    icon = None
    selector_text = None
    skip_selector = False
    show_to_admin_grader = False

    TEMPLATE_BASE = "templates/html/project_navigator/"
    CSS_BASE = "public/css/project_navigator/"
    JS_BASE = "public/js/project_navigator/"

    template = None
    css_file = None
    js_file = None
    initialize_js_function = None
    additional_js_files = ()

    has_author_view = True

    @lazy
    def navigator(self):
        """
        Reference to Project Navigator Block
        """
        return self.get_parent()

    @property
    def course_id(self):
        return getattr(self.runtime, 'course_id', 'all')

    @property
    def allow_admin_grader_access(self):
        return False

    @property
    def is_admin_grader(self):
        return self.navigator.group_project.is_admin_grader

    @property
    def url_name_caption(self):
        return _(u"url_name to link to this {project_navigator_view}:").format(
            project_navigator_view=self.display_name_with_default
        )

    def render_student_view(self, context, add_resources_from=None):
        """
        Common code to render student view
        """
        fragment = Fragment()
        fragment.add_content(loader.render_template(self.TEMPLATE_BASE + self.template, context))

        if self.css_file:
            fragment.add_css_url(self.runtime.local_resource_url(
                self.navigator.group_project, self.CSS_BASE + self.css_file
            ))

        if self.js_file:
            fragment.add_javascript_url(self.runtime.local_resource_url(
                self.navigator.group_project, self.JS_BASE + self.js_file
            ))

        if self.initialize_js_function:
            fragment.initialize_js(self.initialize_js_function)

        for js_file in self.additional_js_files:
            fragment.add_javascript_url(self.runtime.local_resource_url(self.navigator.group_project, js_file))

        if add_resources_from:
            for frag in add_resources_from:
                fragment.add_frag_resources(frag)

        return fragment

    def author_view(self, context):  # pylint: disable=unused-argument, no-self-use
        """
        Studio Preview view
        """
        fragment = Fragment(self.display_name_with_default)
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_frag_resources(url_name_fragment)
        return fragment

    def selector_view(self, context):  # pylint: disable=unused-argument
        """
        Selector view - this view is used by GroupProjectNavigatorXBlock to render selector buttons
        """
        fragment = Fragment()
        context = {'type': self.type, 'display_name': self.display_name_with_default}
        for attribute in ['icon', 'selector_text']:
            if getattr(self, attribute, None) is not None:
                context[attribute] = getattr(self, attribute)
            else:
                context[attribute] = ''
        fragment.add_content(loader.render_template('templates/html/project_navigator/view_selector.html', context))
        return fragment


@XBlock.needs('user')
class NavigationViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Navigation View XBlock - displays Group Project Activities and Stages, completion state and links to navigate to
    any stage in Group Project
    """
    CATEGORY = "gp-v2-navigator-navigation"
    STUDIO_LABEL = _(u"Navigation View")
    type = ViewTypes.NAVIGATION
    icon = u"fa fa-bars"
    display_name_with_default = _(u"Navigation View")
    skip_selector = True
    show_to_admin_grader = True

    template = "navigation_view.html"
    css_file = "navigation_view.css"
    js_file = "navigation_view.js"
    initialize_js_function = "GroupProjectNavigatorNavigationView"

    @property
    def allow_admin_grader_access(self):
        return True

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        activity_fragments = []
        for activity in self.navigator.group_project.activities:
            activity_fragment = activity.render("navigation_view", context)
            activity_fragments.append(activity_fragment)

        context = {'view': self, 'activity_contents': [frag.content for frag in activity_fragments]}
        return self.render_student_view(context, activity_fragments)


class ResourcesViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Resources view XBlock - displays Resources links grouped by Activity
    """
    CATEGORY = "gp-v2-navigator-resources"
    STUDIO_LABEL = _(u"Resources View")
    type = ViewTypes.RESOURCES
    icon = u"fa fa-files-o"
    display_name_with_default = _(u"Resources View")

    template = "resources_view.html"
    css_file = "resources_view.css"
    js_file = "resources_view.js"
    initialize_js_function = "GroupProjectNavigatorResourcesView"

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        activity_fragments = []
        for activity in self.navigator.group_project.activities:
            activity_fragment = activity.render("resources_view", context)
            activity_fragments.append(activity_fragment)

        context = {'view': self, 'activity_contents': [frag.content for frag in activity_fragments]}
        return self.render_student_view(context, activity_fragments)


# pylint-disable=no-init
class SubmissionsViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Submissions View - displays submissions grouped by Activity. Allows uploading new files and downloading
    earlier uploads
    """
    CATEGORY = "gp-v2-navigator-submissions"
    STUDIO_LABEL = _(u"Submissions View")
    type = ViewTypes.SUBMISSIONS
    icon = u"fa fa-upload"
    display_name_with_default = _(u"Upload")

    template = "submissions_view.html"
    css_file = "submissions_view.css"
    js_file = "submissions_view.js"
    initialize_js_function = "GroupProjectNavigatorSubmissionsView"
    additional_js_files = (
        'public/js/vendor/jquery.ui.widget.js',
        'public/js/vendor/jquery.fileupload.js',
        'public/js/vendor/jquery.iframe-transport.js'
    )

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        activity_fragments = []
        for activity in self.navigator.group_project.activities:
            activity_fragment = activity.render("submissions_view", context)
            activity_fragments.append(activity_fragment)

        context = {'view': self, 'activity_contents': [frag.content for frag in activity_fragments]}
        return self.render_student_view(context, activity_fragments)


# pylint-disable=no-init
class AskTAViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Ask a TA view - displays  a form to send message to Teaching Assistant
    """
    CATEGORY = "gp-v2-navigator-ask-ta"
    STUDIO_LABEL = _(u"Ask a TA View")
    type = ViewTypes.ASK_TA
    selector_text = u"TA"
    display_name_with_default = _(u"Ask a TA View")

    template = "ask_ta_view.html"
    css_file = "ask_ta_view.css"
    js_file = "ask_ta_view.js"
    initialize_js_function = "GroupProjectNavigatorAskTAView"

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        img_url = self.runtime.local_resource_url(self.navigator.group_project, "public/img/ask_ta.png")
        context = {'view': self, 'course_id': self.course_id, 'img_url': img_url}
        return self.render_student_view(context)


PROJECT_NAVIGATOR_VIEW_TYPES = (
    NavigationViewXBlock.CATEGORY,
    ResourcesViewXBlock.CATEGORY,
    SubmissionsViewXBlock.CATEGORY,
    AskTAViewXBlock.CATEGORY
)

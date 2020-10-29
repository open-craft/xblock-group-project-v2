"""
This module contains Project Navigator XBlock and it's children view XBlocks
"""
import pkg_resources
import logging
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from django import utils
from xblock.core import XBlock
from xblock.exceptions import NoSuchUsage
from web_fragments.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.studio_editable import (
    NestedXBlockSpec,
    StudioContainerXBlockMixin,
    StudioEditableXBlockMixin,
    XBlockWithPreviewMixin,
)

from group_project_v2 import messages
from group_project_v2.mixins import (
    AdminAccessControlXBlockMixin,
    ChildrenNavigationXBlockMixin,
    CompletionMixin,
    NoStudioEditableSettingsMixin,
    XBlockWithComponentsMixin,
    XBlockWithUrlNameDisplayMixin,
)

from group_project_v2.utils import (
    DiscussionXBlockShim,
    add_resource,
    gettext as _,
    loader,
)

log = logging.getLogger(__name__)


class ViewTypes(object):
    """
    View type constants
    """
    NAVIGATION = 'navigation'
    RESOURCES = 'resources'
    SUBMISSIONS = 'submissions'
    ASK_TA = 'ask-ta'
    PRIVATE_DISCUSSION = 'private-discussion'


class GroupProjectNavigatorXBlock(
    ChildrenNavigationXBlockMixin,
    XBlockWithComponentsMixin,
    XBlockWithPreviewMixin,
    NoStudioEditableSettingsMixin,
    StudioContainerXBlockMixin,
    CompletionMixin,
    XBlock
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
        return [
            NestedXBlockSpec(NavigationViewXBlock, single_instance=True),
            NestedXBlockSpec(ResourcesViewXBlock, single_instance=True),
            NestedXBlockSpec(SubmissionsViewXBlock, single_instance=True),
            NestedXBlockSpec(AskTAViewXBlock, single_instance=True),
            NestedXBlockSpec(PrivateDiscussionViewXBlock, single_instance=True),
        ]

    def _get_activated_view_type(self, target_block_id):
        try:
            if target_block_id:
                block = self.runtime.get_block(target_block_id)
                if self.get_child_category(block) in PROJECT_NAVIGATOR_VIEW_TYPES:
                    return block.type
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        return ViewTypes.NAVIGATION

    def _sorted_child_views(self):
        all_views = []
        for child_id in self.children:
            view = self.runtime.get_block(child_id)
            if view.available_to_current_user and view.is_view_available:
                all_views.append(view)

        all_views.sort(key=lambda view_instance: view_instance.SORT_ORDER)
        return all_views

    def student_view(self, context):
        """
        Student view
        """
        fragment = Fragment()
        children_items = []
        for view in self._sorted_child_views():
            item = {
                'id': str(view.scope_ids.usage_id).replace("/", ";_"),
                'type': view.type,
            }

            if not view.skip_content:
                child_fragment = view.render('student_view', context)
                item['content'] = child_fragment.content
                fragment.add_fragment_resources(child_fragment)
            else:
                item['content'] = ''

            if not view.skip_selector:
                child_selector_fragment = view.render('selector_view', context)
                item['selector'] = child_selector_fragment.content
                fragment.add_fragment_resources(child_selector_fragment)
            else:
                item['selector'] = ''

            children_items.append(item)

        activate_block_id = self.get_block_id_from_string(context.get('activate_block_id', None))

        js_parameters = {
            'selected_view': self._get_activated_view_type(activate_block_id)
        }

        fragment.add_content(
            loader.render_template(
                'templates/html/project_navigator/project_navigator.html',
                {'children': children_items}
            )
        )
        add_resource(self, 'css', 'public/css/project_navigator/project_navigator.css', fragment)
        add_resource(self, 'javascript', 'public/js/project_navigator/project_navigator.js', fragment)
        fragment.initialize_js("GroupProjectNavigatorBlock", js_parameters)

        return fragment

    def author_preview_view(self, context):
        fragment = Fragment()
        children_contents = []
        for child in self._children:
            child_fragment = child.render('preview_view', context)
            fragment.add_fragment_resources(child_fragment)
            children_contents.append(child_fragment.content)

        fragment.add_content(loader.render_template(
            "templates/html/project_navigator/project_navigator_author_view.html",
            {'navigator': self, 'children_contents': children_contents}
        ))
        add_resource(self, 'css', 'public/css/project_navigator/project_navigator.css', fragment)
        return fragment

    def validate(self):
        validation = super(GroupProjectNavigatorXBlock, self).validate()

        if not self.has_child_of_category(NavigationViewXBlock.CATEGORY):
            validation.add(ValidationMessage(ValidationMessage.ERROR, messages.MUST_CONTAIN_NAVIGATION_VIEW))

        return validation


@XBlock.needs("i18n")
class ProjectNavigatorViewXBlockBase(
    CompletionMixin,
    XBlockWithPreviewMixin,
    StudioEditableXBlockMixin,
    XBlockWithUrlNameDisplayMixin,
    AdminAccessControlXBlockMixin,
    XBlock,  # Moved from start.  Mixins usually come first.
):
    """
    Base class for Project Navigator children XBlocks (views)
    """
    type = None
    icon = None
    selector_text = None
    skip_selector = False
    skip_content = False

    TEMPLATE_BASE = "templates/html/project_navigator/"
    CSS_BASE = "public/css/project_navigator/"
    JS_BASE = "public/js/project_navigator/"

    SORT_ORDER = None

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
        return True

    @property
    def is_admin_grader(self):
        return self.navigator.group_project.is_admin_grader

    @property
    def url_name_caption(self):
        return _(u"url_name to link to this {project_navigator_view}:").format(
            project_navigator_view=self.display_name_with_default
        )

    @classmethod
    def is_view_type_available(cls):
        return True

    @property
    def is_view_available(self):  # pylint: disable=no-self-use
        return True

    @staticmethod
    def resource_string(path):
        """Handy helper for getting resources."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_translation_content(self):
        """
        Returns JS content containing translations for user's language.
        """
        try:
            return self.resource_string('public/js/translations/{lang}/textjs.js'.format(
                lang=utils.translation.to_locale(utils.translation.get_language()),
            ))
        except IOError:
            return self.resource_string('public/js/translations/en/textjs.js')

        @property
        def i18n_service(self):
            """ Obtains translation service """
            return self.runtime.service(self, "i18n")

    def render_student_view(self, context, add_resources_from=None):
        """
        Common code to render student view
        """
        fragment = Fragment()
        fragment.add_content(loader.render_django_template(self.TEMPLATE_BASE + self.template,
                                                           context=context,
                                                           i18n_service=self.i18n_service))

        if self.css_file:
            add_resource(self, 'css', self.CSS_BASE + self.css_file, fragment)

        if self.js_file:
            add_resource(self, 'javascript', self.JS_BASE + self.js_file, fragment)

        if self.initialize_js_function:
            fragment.initialize_js(self.initialize_js_function)

        for js_file in self.additional_js_files:
            add_resource(self, 'javascript', js_file, fragment, via_url=True)

        if add_resources_from:
            for frag in add_resources_from:
                fragment.add_fragment_resources(frag)
        fragment.add_javascript(self.get_translation_content())
        return fragment

    def author_view(self, _context):
        """
        Studio Preview view
        """
        fragment = Fragment(self.display_name_with_default)
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_fragment_resources(url_name_fragment)
        return fragment

    def selector_view(self, _context):
        """
        Selector view - this view is used by GroupProjectNavigatorXBlock to render selector buttons
        """
        fragment = Fragment()
        context = {
            'type': self.type,
            'display_name': self.display_name_with_default,
            'skip_content': self.skip_content
        }
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
    STUDENT_VIEW_TITLE = _(u"Navigation")
    type = ViewTypes.NAVIGATION
    icon = u"fa fa-bars"
    display_name_with_default = STUDIO_LABEL
    skip_selector = True

    SORT_ORDER = 0

    template = "navigation_view.html"
    css_file = "navigation_view.css"
    js_file = "navigation_view.js"
    initialize_js_function = "GroupProjectNavigatorNavigationView"

    def student_view(self, context):
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
    STUDENT_VIEW_TITLE = _(u"Resources")
    type = ViewTypes.RESOURCES
    icon = u"fa fa-files-o"
    display_name_with_default = STUDIO_LABEL

    SORT_ORDER = 2

    template = "resources_view.html"
    css_file = "resources_view.css"
    js_file = "resources_view.js"
    initialize_js_function = "GroupProjectNavigatorResourcesView"

    def student_view(self, context):
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
    STUDENT_VIEW_TITLE = _(u"Upload")
    type = ViewTypes.SUBMISSIONS
    icon = u"fa fa-upload"
    display_name_with_default = STUDIO_LABEL

    SORT_ORDER = 1

    template = "submissions_view.html"
    css_file = "submissions_view.css"
    js_file = "submissions_view.js"
    initialize_js_function = "GroupProjectNavigatorSubmissionsView"
    additional_js_files = (
        'public/js/vendor/jquery.ui.widget.js',
        'public/js/vendor/jquery.fileupload.js',
        'public/js/vendor/jquery.iframe-transport.js'
    )

    @property
    def allow_admin_grader_access(self):
        return True

    def student_view(self, context):
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
    STUDENT_VIEW_TITLE = _(u"Ask a McKinsey TA")
    type = ViewTypes.ASK_TA
    selector_text = u"TA"
    display_name_with_default = STUDIO_LABEL

    SORT_ORDER = 4

    template = "ask_ta_view.html"
    css_file = "ask_ta_view.css"
    js_file = "ask_ta_view.js"
    initialize_js_function = "GroupProjectNavigatorAskTAView"

    @property
    def allow_admin_grader_access(self):
        return False

    @classmethod
    def is_view_type_available(cls):
        # TODO: LMS support - check if TAs are available at all
        return True

    def student_view(self, context):
        """
        Student view
        """
        img_url = self.runtime.local_resource_url(self, "public/img/ask_ta.png")
        context = {'view': self, 'course_id': self.course_id, 'img_url': img_url}
        return self.render_student_view(context)


class PrivateDiscussionViewXBlock(ProjectNavigatorViewXBlockBase):
    CATEGORY = 'gp-v2-navigator-private-discussion'
    STUDIO_LABEL = _(u"Private Discussion View")
    type = ViewTypes.PRIVATE_DISCUSSION
    icon = 'fa fa-comment'
    skip_content = True  # there're no content in this view so far - it only shows discussion in a popup
    display_name_with_default = STUDIO_LABEL

    SORT_ORDER = 3

    js_file = "private_discussion_view.js"
    initialize_js_function = "GroupProjectPrivateDiscussionView"

    def _project_has_discussion(self):
        return self.navigator.group_project.has_child_of_category(DiscussionXBlockShim.CATEGORY)

    @property
    def is_view_available(self):
        return self._project_has_discussion()

    def selector_view(self, context):
        """
        Selector view - this view is used by GroupProjectNavigatorXBlock to render selector buttons
        """
        fragment = super(PrivateDiscussionViewXBlock, self).selector_view(context)
        add_resource(self, 'javascript', self.JS_BASE + self.js_file, fragment)
        fragment.initialize_js(self.initialize_js_function)
        return fragment

    def validate(self):
        validation = super(PrivateDiscussionViewXBlock, self).validate()
        if not self._project_has_discussion():
            validation.add(ValidationMessage(
                ValidationMessage.WARNING,
                messages.NO_DISCUSSION_IN_GROUP_PROJECT.format(block_type=self.STUDIO_LABEL)
            ))

        return validation


PROJECT_NAVIGATOR_VIEW_TYPES = (
    NavigationViewXBlock.CATEGORY,
    ResourcesViewXBlock.CATEGORY,
    SubmissionsViewXBlock.CATEGORY,
    AskTAViewXBlock.CATEGORY,
    PrivateDiscussionViewXBlock.CATEGORY
)

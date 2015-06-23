import logging

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict, Float, Integer
from xblock.fragment import Fragment

from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioContainerXBlockMixin

log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)


class GroupProjectNavigatorXBlock(StudioContainerXBlockMixin, XBlock):
    has_score = False
    has_children = True

    def student_view(self, context):
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=False, can_add=False)
        return fragment

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(loader.render_template('templates/html/group_project_navigator_add_buttons.html', {}))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        return fragment


class NavigationViewXBlock(XBlock):
    def student_view(self):
        fragment = Fragment()
        fragment.add_content("<div>I'm navigator</div>")
        return fragment


class ResourcesViewXBlock(XBlock):
    def student_view(self):
        fragment = Fragment()
        fragment.add_content("<div>I'm resources</div>")
        return fragment


class SubmissionsViewXBlock(XBlock):
    def student_view(self):
        fragment = Fragment()
        fragment.add_content("<div>I'm submissions</div>")
        return fragment


class AskTAViewXBlock(XBlock):
    def student_view(self):
        fragment = Fragment()
        fragment.add_content("<div>I'm ask a TA</div>")
        return fragment
from xblock.core import XBlock
from xblock.fragment import Fragment

from xblockutils.studio_editable import StudioContainerXBlockMixin

from ..utils import loader, load_resource


class ViewTypes(object):
    NAVIGATION = 'navigation'
    RESOURCES = 'resources'
    SUBMISSIONS = 'submissions'
    ASK_TA = 'ask-ta'


class GroupProjectNavigatorXBlock(StudioContainerXBlockMixin, XBlock):
    INITIAL_VIEW = ViewTypes.NAVIGATION

    display_name_with_default = "Group Project Navigator"

    editable = False
    has_score = False
    has_children = True

    @property
    def group_project(self):
        return self.get_parent()

    def student_view(self, context):
        fragment = Fragment()
        children_items = []
        for child_id in self.children:
            child = self.runtime.get_block(child_id)
            # child_fragment = child.render('student_view', context)
            child_fragment = child.student_view(context)

            fragment.add_frag_resources(child_fragment)
            children_items.append({
                'type': child.type,
                'display_name': child.display_name_with_default,
                'content': child_fragment.content
            })

        fragment.add_content(
            loader.render_template('templates/html/group_project_navigator.html', {'children': children_items})
        )
        fragment.add_css_url(
            self.runtime.local_resource_url(self.group_project, 'public/css/group_project_navigator.css')
        )
        fragment.add_javascript(load_resource('public/js/project_navigator.js'))
        fragment.initialize_js("GroupProjectNavigatorBlock")

        return fragment

    def author_preview_view(self, context):
        """
        Child blocks can override this to add a custom preview shown to authors in Studio when
        not editing this block's children.
        """
        return self.student_view(context)

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(loader.render_template('templates/html/group_project_navigator_add_buttons.html', {}))
        fragment.add_css_url(self.runtime.local_resource_url(self.group_project, 'public/css/group_project_edit.css'))
        return fragment


class NavigationViewXBlock(XBlock):
    display_name_with_default = u"Navigation"
    type = ViewTypes.NAVIGATION

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm navigator")
        return fragment


class ResourcesViewXBlock(XBlock):
    display_name_with_default = u"Resources"
    type = ViewTypes.RESOURCES

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm resources")
        return fragment


class SubmissionsViewXBlock(XBlock):
    display_name_with_default = u"Submissions"
    type = ViewTypes.SUBMISSIONS

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm submissions")
        return fragment


class AskTAViewXBlock(XBlock):
    display_name_with_default = u"Ask a TA"
    type = ViewTypes.ASK_TA

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm ask a TA")
        return fragment
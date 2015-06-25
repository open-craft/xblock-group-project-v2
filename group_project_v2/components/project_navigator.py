from xblock.core import XBlock
from xblock.fragment import Fragment

from xblockutils.studio_editable import StudioContainerXBlockMixin
from group_project_v2.components.stage import StageState
from group_project_v2.project_api import project_api

from ..utils import loader, load_resource, gettext as _


class ViewTypes(object):
    NAVIGATION = 'navigation'
    RESOURCES = 'resources'
    SUBMISSIONS = 'submissions'
    ASK_TA = 'ask-ta'


class GroupProjectNavigatorXBlock(StudioContainerXBlockMixin, XBlock):
    INITIAL_VIEW = ViewTypes.NAVIGATION

    display_name_with_default = _(u"Group Project Navigator")

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
            child_fragment = child.student_view(context)
            child_selector_fragment = child.selector_view(context)

            fragment.add_frag_resources(child_fragment)
            children_items.append({
                'type': child.type,
                'content': child_fragment.content,
                'selector': child_selector_fragment.content
            })

        fragment.add_content(
            loader.render_template('templates/html/project_navigator/project_navigator.html', {'children': children_items})
        )
        fragment.add_css_url(
            self.runtime.local_resource_url(self.group_project, 'public/css/group_project_navigator.css')
        )
        fragment.add_javascript(load_resource('public/js/project_navigator/project_navigator.js'))
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
        fragment.add_content(loader.render_template('templates/html/project_navigator/add_buttons.html', {}))
        fragment.add_css_url(self.runtime.local_resource_url(self.group_project, 'public/css/group_project_edit.css'))
        return fragment


class ProjectNavigatorViewXBlockBase(XBlock):
    type = None
    icon = None
    selector_text = None

    @property
    def navigator(self):
        return self.get_parent()

    def selector_view(self, context):
        fragment = Fragment()
        context = {'type': self.type, 'display_name': self.display_name_with_default}
        for attribute in ['icon', 'selector_text']:
            if getattr(self, attribute, None) is not None:
                context[attribute] = getattr(self, attribute)
        fragment.add_content(loader.render_template('templates/html/project_navigator/view_selector.html', context))
        return fragment


@XBlock.needs('user')
class NavigationViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.NAVIGATION
    icon = u"fa-bars"
    display_name_with_default = _(u"Navigation")

    ICONS_MAP = {
        StageState.NOT_STARTED: u'',
        StageState.INCOMPLETE: u'fa-circle',
        StageState.COMPLETED: u'fa-check-circle'
    }

    def get_stage_state(self, activity_id, stage):
        user_service = self.runtime.service(self, 'user')
        user_id = user_service.get_current_user().opt_attrs.get('edx-platform.user_id', None)

        users_in_group, completed_users = project_api.get_stage_state(
            self.course_id,
            activity_id,
            user_id,
            stage.id
        )

        if users_in_group == completed_users:
            return StageState.COMPLETED
        if completed_users:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def student_view(self, context):
        navigation_map = []

        for activity in self.navigator.group_project.activities:
            stages_data = []
            for stage in activity.get_group_activity().activity_stages:
                stage_state = self.get_stage_state(activity.scope_ids.usage_id, stage)
                data = {'stage': stage, 'state': stage_state}
                if stage_state in self.ICONS_MAP:
                    data['icon'] = self.ICONS_MAP[stage_state]
                stages_data.append(data)

            navigation_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'stages': stages_data
            })

        fragment = Fragment()
        context = {'view': self, 'navigation_map': navigation_map}
        fragment.add_content(loader.render_template("templates/html/project_navigator/navigation_view.html", context))

        return fragment


class ResourcesViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.RESOURCES
    icon = u"fa-files-o"
    display_name_with_default = _(u"Resources")

    def student_view(self, context):
        resources_map = []
        for activity in self.navigator.group_project.activities:
            resources_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'stages': activity.get_group_activity().activity_stages
            })

        fragment = Fragment()
        context = {'view': self, 'resources_map': resources_map}
        fragment.add_content(loader.render_template("templates/html/project_navigator/resources_view.html", context))
        return fragment


class SubmissionsViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.SUBMISSIONS
    icon = u"fa-upload"
    display_name_with_default = _(u"Submissions")

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm submissions")
        return fragment


class AskTAViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.ASK_TA
    selector_text = u"TA"
    display_name_with_default = _(u"Ask a TA")

    def student_view(self, context):
        fragment = Fragment()
        fragment.add_content(u"I'm ask a TA")
        return fragment
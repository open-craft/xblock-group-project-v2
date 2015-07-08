"""
This module contains Project Navigator XBlock and it's children view XBlocks
"""
import itertools
import json
import logging
from lazy.lazy import lazy
import webob
from xblock.core import XBlock
from xblock.fragment import Fragment
from opaque_keys.edx.locator import BlockUsageLocator

from xblockutils.studio_editable import StudioContainerXBlockMixin, StudioEditableXBlockMixin

from group_project_v2.api_error import ApiError
from group_project_v2.stage import StageState
from group_project_v2.project_api import project_api
from group_project_v2.upload_file import UploadFile
from group_project_v2.utils import loader, gettext as _


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ViewTypes(object):
    """
    View type constants
    """
    NAVIGATION = 'navigation'
    RESOURCES = 'resources'
    SUBMISSIONS = 'submissions'
    ASK_TA = 'ask-ta'


class GroupProjectNavigatorXBlock(StudioContainerXBlockMixin, XBlock):
    """
    XBlock that provides basic layout and switching between children XBlocks (views)
    Should only be added as a child to GroupProjectXBlock
    """
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

    def student_view(self, context):
        """
        Student view
        """
        fragment = Fragment()
        children_items = []
        for child_id in self.children:
            child = self.runtime.get_block(child_id)
            child_fragment = child.render('student_view', context)

            item = {
                'type': child.type,
                'content': child_fragment.content,
            }

            fragment.add_frag_resources(child_fragment)

            if not child.skip_selector:
                child_selector_fragment = child.selector_view(context)
                item['selector'] = child_selector_fragment.content
                fragment.add_frag_resources(child_selector_fragment)
            else:
                item['selector'] = ''

            children_items.append(item)

        fragment.add_content(
            loader.render_template(
                'templates/html/project_navigator/project_navigator.html',
                {'children': children_items}
            )
        )
        fragment.add_css_url(self.runtime.local_resource_url(
            self.group_project, 'public/css/project_navigator/project_navigator.css'
        ))
        fragment.add_javascript_url(self.runtime.local_resource_url(
            self.group_project, 'public/js/project_navigator/project_navigator.js'
        ))
        fragment.initialize_js("GroupProjectNavigatorBlock")

        return fragment

    def author_preview_view(self, context):
        """
        Studio Preview view
        """
        # Can't use student view as it fails with 404 if new activity is added after project navigator:
        # throws 404 because navigation view searches for completions for all available activities.
        # Draft activity is visible to nav view, but not to completions api, resulting in 404.
        # Anyway, it looks like it needs some other studio preview representation
        return Fragment()

    def author_edit_view(self, context):
        """
        Studio edit view
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(loader.render_template('templates/html/project_navigator/add_buttons.html', {}))
        fragment.add_css_url(self.runtime.local_resource_url(self.group_project, 'public/css/group_project_edit.css'))
        return fragment


class ProjectNavigatorViewXBlockBase(XBlock, StudioEditableXBlockMixin):
    """
    Base class for Project Navigator children XBlocks (views)
    """
    type = None
    icon = None
    selector_text = None
    skip_selector = False

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

    def render_student_view(self, context):
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

        return fragment

    def author_view(self, context):  # pylint: disable=unused-argument, no-self-use
        """
        Studio Preview view
        """
        # Can't use student view as it they usually result in sending some requests to api - this is costly and often
        # crash entire XBlock in studio due to 404 response codes
        return Fragment()

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
    type = ViewTypes.NAVIGATION
    icon = u"fa-bars"
    display_name_with_default = _(u"Navigation")
    skip_selector = True

    template = "navigation_view.html"
    css_file = "navigation_view.css"
    js_file = "navigation_view.js"
    initialize_js_function = "GroupProjectNavigatorNavigationView"

    def get_stage_state(self, activity_id, stage):
        """
        Gets stage completion state
        """
        user_service = self.runtime.service(self, 'user')
        user_id = user_service.get_current_user().opt_attrs.get('edx-platform.user_id', None)

        users_in_group, completed_users = project_api.get_stage_state(
            self.course_id,
            activity_id,
            user_id,
            stage.id
        )

        if not users_in_group or not completed_users:
            return StageState.NOT_STARTED
        if users_in_group <= completed_users:
            return StageState.COMPLETED
        if users_in_group & completed_users:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        navigation_map = []

        for activity in self.navigator.group_project.activities:
            stages_data = []
            for stage in activity.stages:
                stage_state = self.get_stage_state(activity.scope_ids.usage_id, stage)
                stages_data.append({'stage': stage, 'state': stage_state})

            navigation_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'stages': stages_data
            })

        context = {'view': self, 'navigation_map': navigation_map}
        return self.render_student_view(context)


class ResourcesViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Resources view XBlock - displays Resources links grouped by Activity
    """
    type = ViewTypes.RESOURCES
    icon = u"fa-files-o"
    display_name_with_default = _(u"Resources")

    template = "resources_view.html"
    css_file = "resources_view.css"
    js_file = "resources_view.js"
    initialize_js_function = "GroupProjectNavigatorResourcesView"

    def student_view(self, context):  # pylint: disable=unused-argument
        """
        Student view
        """
        resources_map = []
        resource_fragments = []
        for activity in self.navigator.group_project.activities:
            resources = list(itertools.chain(*[
                stage.resources for stage in activity.stages

            ]))
            fragments = [res.render('project_navigator_view', context) for res in resources]
            resource_fragments.extend(fragments)

            resources_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'resources': [fragment.content for fragment in fragments],
            })

        context = {'view': self, 'resources_map': resources_map}
        fragment = self.render_student_view(context)
        for resource_fragment in resource_fragments:
            fragment.add_frag_resources(resource_fragment)

        return fragment


# pylint-disable=no-init
@XBlock.needs('user')
@XBlock.wants('notifications')
class SubmissionsViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Submissions View - displays submissions grouped by Activity. Allows uploading new files and downloading
    earlier uploads
    """
    type = ViewTypes.SUBMISSIONS
    icon = u"fa-upload"
    display_name_with_default = _(u"Submissions")

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
        # TODO: should have used `include` in template, but it can't find the template: resource loader does
        # not know how to do that
        submissions_map = []
        stage_fragments = []
        for activity in self.navigator.group_project.activities:
            activity.update_submission_data(activity.workgroup["id"])
            stages = [stage for stage in activity.stages if stage.submissions_stage]
            stage_frags = [stage.render('project_navigator_submissions_view', context) for stage in stages]
            stage_fragments.extend(stage_frags)

            submissions_required = any(True for stage in stages if len(stage.submissions) > 0)
            submissions_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'submissions_required': submissions_required,
                'stage_contents': [frag.content for frag in stage_frags],
            })

        context = {'view': self, 'submissions_map': submissions_map}

        fragment = self.render_student_view(context)
        for resource_fragment in stage_fragments:
            fragment.add_frag_resources(resource_fragment)

        return fragment

    # TODO: When Stages become XBlocks this method should become a handler on SubmissionsStage XBlock
    @XBlock.handler
    def upload_submission(self, request, suffix=''):  # pylint: disable=unused-argument
        """
        Handles submission upload and marks stage as completed if all submissions in stage have uploads.
        """
        activity_id, stage_id = request.POST['activity_id'], request.POST['stage_id']
        target_activity = self.runtime.get_block(BlockUsageLocator.from_string(activity_id))

        response_data = {"message": _("File(s) successfully submitted")}
        failure_code = 0
        try:
            context = {
                "user_id": target_activity.user_id,
                "group_id": target_activity.workgroup['id'],
                "project_api": project_api,
                "course_id": target_activity.course_id
            }

            upload_files = self.persist_and_submit_files(target_activity, target_activity, context, request.params)

            response_data["submissions"] = {
                uploaded_file.submission_id: uploaded_file.file_url for uploaded_file in upload_files
            }

            target_activity.update_submission_data(target_activity.workgroup['id'])

            target_stage = [stage for stage in target_activity.stages if stage.id == stage_id][0]
            if target_stage.has_all_submissions:
                for user in target_activity.workgroup["users"]:
                    target_activity.mark_complete_stage(user["id"], target_stage.id)

                response_data["new_stage_states"] = [
                    {
                        "activity_id": activity_id,
                        "stage_id": stage_id,
                        "state": StageState.COMPLETED
                    }
                ]

        except Exception as exception:  # pylint: disable=broad-except
            log.exception(exception)
            failure_code = 500
            if isinstance(exception, ApiError):
                failure_code = exception.code
            if not hasattr(exception, "message"):
                exception.message = _("Error uploading at least one file")
            response_data.update({"message": exception.message})

        response = webob.response.Response(body=json.dumps(response_data))
        if failure_code:
            response.status_code = failure_code

        return response

    def send_file_upload_notification(self, target_activity):
        """
        Helper method to emit notifications service event for submission upload
        """
        # See if the xBlock Notification Service is available, and - if so -
        # dispatch a notification to the entire workgroup that a file has been uploaded
        # Note that the NotificationService can be disabled, so it might not be available
        # in the list of services
        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            target_activity.fire_file_upload_notification(notifications_service)

    def persist_and_submit_files(self, target_activity, activity, context, request_parameters):
        """
        Saves uploaded files to their permanent location, sends them to submissions backend and emits submission events
        """
        upload_files = [
            UploadFile(request_parameters[submission.id].file, submission.id, context)
            for submission in activity.submissions if submission.id in request_parameters
        ]

        # Save the files first
        for uploaded_file in upload_files:
            try:
                uploaded_file.save_file()
            except Exception as save_file_error:  # pylint: disable=broad-except
                original_message = save_file_error.message if hasattr(save_file_error, "message") else ""
                save_file_error.message = _("Error storing file {} - {}").format(
                    uploaded_file.file.name, original_message
                )
                raise

        # They all got saved... note the submissions
        at_least_one_success = False
        for uploaded_file in upload_files:
            try:
                uploaded_file.submit()
                # Emit analytics event...
                self.runtime.publish(
                    self,
                    "activity.received_submission",
                    {
                        "submission_id": uploaded_file.submission_id,
                        "filename": uploaded_file.file.name,
                        "content_id": target_activity.content_id,
                        "group_id": target_activity.workgroup['id'],
                        "user_id": target_activity.user_id,
                    }
                )
                at_least_one_success = True
            except Exception as save_record_error:  # pylint: disable=broad-except
                original_message = save_record_error.message if hasattr(save_record_error, "message") else ""
                save_record_error.message = _("Error recording file information {} - {}").format(
                    uploaded_file.file.name, original_message
                )
                raise

        if at_least_one_success:
            self.send_file_upload_notification(target_activity)

        return upload_files


# pylint-disable=no-init
class AskTAViewXBlock(ProjectNavigatorViewXBlockBase):
    """
    Ask a TA view - displays  a form to send message to Teaching Assistant
    """
    type = ViewTypes.ASK_TA
    selector_text = u"TA"
    display_name_with_default = _(u"Ask a TA")

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

import itertools
import json
import logging
import webob
from xblock.core import XBlock
from xblock.fragment import Fragment
from opaque_keys.edx.locator import BlockUsageLocator

from xblockutils.studio_editable import StudioContainerXBlockMixin
from group_project_v2.api_error import ApiError
from group_project_v2.components.stage import StageState
from group_project_v2.project_api import project_api
from group_project_v2.upload_file import UploadFile

from ..utils import loader, gettext as _


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


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
        Child blocks can override this to add a custom preview shown to authors in Studio when
        not editing this block's children.
        """
        # Can't use student view as it fails with 404 if new activity is added after project navigator:
        # throws 404 because navigation view searches for completions for all available activities.
        # Draft activity is visible to nav view, but not to completions api, resulting in 404.
        # Anyway, it looks like it needs some other studio preview representation
        return Fragment()

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
    skip_selector = False

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
    skip_selector = True

    def get_stage_state(self, activity_id, stage):
        user_service = self.runtime.service(self, 'user')
        user_id = user_service.get_current_user().opt_attrs.get('edx-platform.user_id', None)

        users_in_group, completed_users = project_api.get_stage_state(
            self.course_id,
            activity_id,
            user_id,
            stage.id
        )

        if users_in_group <= completed_users:
            return StageState.COMPLETED
        if completed_users:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def student_view(self, context):  # pylint: disable=unused-argument
        navigation_map = []

        for activity in self.navigator.group_project.activities:
            stages_data = []
            for stage in activity.get_group_activity().activity_stages:
                stage_state = self.get_stage_state(activity.scope_ids.usage_id, stage)
                stages_data.append({'stage': stage, 'state': stage_state})

            navigation_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'stages': stages_data
            })

        fragment = Fragment()
        context = {'view': self, 'navigation_map': navigation_map}
        fragment.add_content(loader.render_template("templates/html/project_navigator/navigation_view.html", context))
        fragment.add_javascript_url(self.runtime.local_resource_url(
            self.navigator.group_project, "public/js/project_navigator/navigation_view.js"
        ))
        fragment.initialize_js("GroupProjectNavigatorNavigationView")

        return fragment


class ResourcesViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.RESOURCES
    icon = u"fa-files-o"
    display_name_with_default = _(u"Resources")

    def student_view(self, context):  # pylint: disable=unused-argument
        resources_map = []
        for activity in self.navigator.group_project.activities:
            resources = list(itertools.chain(*[
                stage.resources for stage in activity.get_group_activity().activity_stages
            ]))
            resources_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'resources': resources,
            })

        fragment = Fragment()
        context = {'view': self, 'resources_map': resources_map}
        fragment.add_content(loader.render_template("templates/html/project_navigator/resources_view.html", context))
        return fragment


# pylint-disable=no-init
@XBlock.needs('user')
@XBlock.wants('notifications')
class SubmissionsViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.SUBMISSIONS
    icon = u"fa-upload"
    display_name_with_default = _(u"Submissions")

    def _get_submissions_map(self):
        submissions_map = []
        for activity in self.navigator.group_project.activities:
            group_activity = activity.get_group_activity()
            group_activity.update_submission_data(
                project_api.get_latest_workgroup_submissions_by_id(activity.workgroup["id"])
            )
            stages = [stage for stage in group_activity.activity_stages if stage.submissions_stage]
            submissions_required = any(True for stage in stages if len(stage.submissions) > 0)
            submissions_map.append({
                'id': activity.scope_ids.usage_id,
                'display_name': activity.display_name,
                'submissions_required': submissions_required,
                'stages': stages,
            })

        return submissions_map

    def student_view(self, context):  # pylint: disable=unused-argument
        fragment = Fragment()
        # FIXME: should have used `include` in template, but it can't find the template: likely resource loader does
        # not know how to do that
        submission_links = loader.render_template(
            "templates/html/project_navigator/submission_links.html",
            {'course_id': self.course_id, 'submissions_map': self._get_submissions_map()}
        )

        context = {'view': self, 'submission_links': submission_links}
        fragment.add_content(loader.render_template("templates/html/project_navigator/submissions_view.html", context))
        fragment.add_css_url(self.runtime.local_resource_url(
            self.navigator.group_project, "public/css/project_navigator/submissions_view.css"
        ))
        fragment.add_javascript_url(self.runtime.local_resource_url(
            self.navigator.group_project, "public/js/project_navigator/submissions_view.js"
        ))
        fragment.initialize_js("GroupProjectNavigatorSubmissionsView")
        return fragment

    @XBlock.handler
    def refresh_submission_links(self, request, suffix=''):
        html_output = loader.render_template(
            '/templates/html/project_navigator/submission_links.html',
            {"submissions_map": self._get_submissions_map()}
        )

        return webob.response.Response(body=json.dumps({"html": html_output}))

    # TODO: When Stages become XBlocks this method should become a handler on SubmissionsStage XBlock
    @XBlock.handler
    def upload_submission(self, request, suffix=''):
        activity_id, stage_id = request.POST['activity_id'], request.POST['stage_id']
        target_activity = self.runtime.get_block(BlockUsageLocator.from_string(activity_id))

        response_data = {"message": _("File(s) successfully submitted")}
        failure_code = 0
        try:
            group_activity = target_activity.get_group_activity()

            context = {
                "user_id": target_activity.user_id,
                "group_id": target_activity.workgroup['id'],
                "project_api": project_api,
                "course_id": target_activity.course_id
            }

            upload_files = self.persist_and_submit_files(target_activity, group_activity, context, request.params)

            response_data.update({uf.submission_id: uf.file_url for uf in upload_files})

            group_activity.update_submission_data(
                project_api.get_latest_workgroup_submissions_by_id(target_activity.workgroup['id'])
            )

            target_stage = [stage for stage in group_activity.activity_stages if stage.id == stage_id][0]
            if target_stage.has_all_submissions:
                for u in target_activity.workgroup["users"]:
                    target_activity.mark_complete_stage(u["id"], target_stage.id)

                response_data["new_stage_states"] = [
                    {
                        "activity_id": activity_id,
                        "stage_id": stage_id,
                        "state": StageState.COMPLETED
                    }
                ]

        except Exception as e:  # pylint: disable=broad-except
            log.exception(e)
            failure_code = 500
            if isinstance(e, ApiError):
                failure_code = e.code
            if not hasattr(e, "message"):
                e.message = _("Error uploading at least one file")
            response_data.update({"message": e.message})

        response = webob.response.Response(body=json.dumps(response_data))
        if failure_code:
            response.status_code = failure_code

        return response

    def send_file_upload_notification(self):
        # See if the xBlock Notification Service is available, and - if so -
        # dispatch a notification to the entire workgroup that a file has been uploaded
        # Note that the NotificationService can be disabled, so it might not be available
        # in the list of services
        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            self.fire_file_upload_notification(notifications_service)

    def persist_and_submit_files(self, target_activity, group_activity, context, request_parameters):
        upload_files = [
            UploadFile(request_parameters[submission.id].file, submission.id, context)
            for submission in group_activity.submissions if submission.id in request_parameters
        ]

        # Save the files first
        for uf in upload_files:
            try:
                uf.save_file()
            except Exception as save_file_error:  # pylint: disable=broad-except
                original_message = save_file_error.message if hasattr(save_file_error, "message") else ""
                save_file_error.message = _("Error storing file {} - {}").format(uf.file.name, original_message)
                raise

        # They all got saved... note the submissions
        at_least_one_success = False
        for uf in upload_files:
            try:
                uf.submit()
                # Emit analytics event...
                self.runtime.publish(
                    self,
                    "group_activity.received_submission",
                    {
                        "submission_id": uf.submission_id,
                        "filename": uf.file.name,
                        "content_id": target_activity.content_id,
                        "group_id": target_activity.workgroup['id'],
                        "user_id": target_activity.user_id,
                    }
                )
                at_least_one_success = True
            except Exception as save_record_error:  # pylint: disable=broad-except
                original_message = save_record_error.message if hasattr(save_record_error, "message") else ""
                save_record_error.message = _("Error recording file information {} - {}").format(uf.file.name,
                                                                                                 original_message)
                raise

            if at_least_one_success:
                self.send_file_upload_notification()

        return upload_files


# pylint-disable=no-init
class AskTAViewXBlock(ProjectNavigatorViewXBlockBase):
    type = ViewTypes.ASK_TA
    selector_text = u"TA"
    display_name_with_default = _(u"Ask a TA")

    def student_view(self, context):  # pylint: disable=unused-argument
        fragment = Fragment()
        fragment.add_content(u"I'm ask a TA")
        return fragment

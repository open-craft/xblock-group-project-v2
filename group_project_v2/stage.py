from collections import OrderedDict, namedtuple
from datetime import datetime
import json
import logging
from lazy.lazy import lazy
import pytz
import webob
from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime, Boolean
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin
from group_project_v2.api_error import ApiError

from group_project_v2.review import GroupProjectReviewQuestionXBlock, GroupProjectReviewAssessmentXBlock
from group_project_v2.project_api import project_api
from group_project_v2.upload_file import UploadFile
from group_project_v2.utils import loader, inner_html, format_date, gettext as _, ChildrenNavigationXBlockMixin, \
    build_date_field

log = logging.getLogger(__name__)


class StageType(object):
    NORMAL = 'normal'
    UPLOAD = 'upload'
    PEER_REVIEW = 'peer_review'
    PEER_ASSESSMENT = 'peer_assessment'
    GROUP_REVIEW = 'group_review'
    GROUP_ASSESSMENT = 'group_assessment'


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


class ResourceType(object):
    NORMAL = 'normal'
    OOYALA_VIDEO = 'ooyala'


class GroupProjectResourceXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-resource"

    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/project_navigator/resource_xblock_view.html'

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the resource"),
        scope=Scope.settings,
        default="Group Project V2 Resource"
    )

    description = String(
        display_name=_(u"Resource Description"),
        scope=Scope.settings
    )

    resource_location = String(
        display_name=_(u"Resource location"),
        help=_(u"A url to download/view the resource"),
        scope=Scope.settings,
    )

    grading_criteria = Boolean(
        display_name=_(u"Grading criteria?"),
        help=_(u"If true, resource will be treated as grading criteria"),
        scope=Scope.settings,
        default=False
    )

    editable_fields = ('display_name', 'description', 'resource_location', 'grading_criteria')

    def student_view(self, context):
        return Fragment()

    def author_view(self, context):
        return self.resources_view(context)

    def resources_view(self, context):
        fragment = Fragment()
        render_context = {'resource': self}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        return fragment


SubmissionUpload = namedtuple("SubmissionUpload", "location file_name submission_date user_details")


@XBlock.needs('user')
@XBlock.wants('notifications')
class GroupProjectSubmissionXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-submission"
    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/project_navigator/submission_xblock_view.html'

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the submission"),
        scope=Scope.settings,
        default="Group Project V2 Submission"
    )

    description = String(
        display_name=_(u"Resource Description"),
        scope=Scope.settings
    )

    upload_id = String(
        display_name=_(u"Upload ID"),
        help=_(U"This string is used as an identifier for an upload. "
               U"Submissions sharing the same Upload ID will be updated simultaneously"),
    )

    editable_fields = ('display_name', 'description', 'upload_id')

    @lazy
    def stage(self):
        return self.get_parent()

    def get_upload(self, group_id):
        submission_map = project_api.get_latest_workgroup_submissions_by_id(group_id)
        submission_data = submission_map.get(self.upload_id, None)

        if submission_data is None:
            return None

        return SubmissionUpload(
            submission_data["document_url"],
            submission_data["document_filename"],
            format_date(build_date_field(submission_data["modified"])),
            submission_data.get("user_details", None)
        )

    @property
    def upload(self):
        return self.get_upload(self.stage.activity.workgroup["id"])

    def student_view(self, context):
        return Fragment()

    def submissions_view(self, context):
        fragment = Fragment()
        render_context = {'submission': self, 'upload': self.upload}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/submission.js'))
        fragment.initialize_js("GroupProjectSubmissionBlock")
        return fragment

    @XBlock.handler
    def upload_submission(self, request, suffix=''):  # pylint: disable=unused-argument
        """
        Handles submission upload and marks stage as completed if all submissions in stage have uploads.
        """
        target_activity = self.stage.activity
        stage_id = self.stage.id

        response_data = {"message": _("File(s) successfully submitted")}
        failure_code = 0
        try:
            context = {
                "user_id": target_activity.user_id,
                "group_id": target_activity.workgroup['id'],
                "project_api": project_api,
                "course_id": target_activity.course_id
            }

            uploaded_file = self.persist_and_submit_file(target_activity, context, request.params[self.upload_id].file)

            response_data["submissions"] = {
                uploaded_file.submission_id: uploaded_file.file_url
            }

            if self.stage.has_all_submissions:
                for user in target_activity.workgroup["users"]:
                    self.stage.mark_complete(user["id"])

                response_data["new_stage_states"] = [
                    {
                        "activity_id": str(target_activity.id),
                        "stage_id": str(stage_id),
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

    def persist_and_submit_file(self, activity, context, file_stream):
        """
        Saves uploaded files to their permanent location, sends them to submissions backend and emits submission events
        """
        uploaded_file = UploadFile(file_stream, self.upload_id, context)

        # Save the files first
        try:
            uploaded_file.save_file()
        except Exception as save_file_error:  # pylint: disable=broad-except
            original_message = save_file_error.message if hasattr(save_file_error, "message") else ""
            save_file_error.message = _("Error storing file {} - {}").format(uploaded_file.file.name, original_message)
            raise

        # It have been saved... note the submission
        try:
            uploaded_file.submit()
            # Emit analytics event...
            self.runtime.publish(
                self,
                "activity.received_submission",
                {
                    "submission_id": uploaded_file.submission_id,
                    "filename": uploaded_file.file.name,
                    "content_id": activity.content_id,
                    "group_id": activity.workgroup['id'],
                    "user_id": activity.user_id,
                }
            )
        except Exception as save_record_error:  # pylint: disable=broad-except
            original_message = save_record_error.message if hasattr(save_record_error, "message") else ""
            save_record_error.message = _("Error recording file information {} - {}").format(
                uploaded_file.file.name, original_message
            )
            raise

        # See if the xBlock Notification Service is available, and - if so -
        # dispatch a notification to the entire workgroup that a file has been uploaded
        # Note that the NotificationService can be disabled, so it might not be available
        # in the list of services
        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            activity.fire_file_upload_notification(notifications_service)

        return uploaded_file


class BaseGroupActivityStage(XBlock, ChildrenNavigationXBlockMixin,
                             StudioEditableXBlockMixin, StudioContainerXBlockMixin):
    submissions_stage = False

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the stage"),
        scope=Scope.settings,
        default="Group Project V2 Stage"
    )

    open_date = DateTime(
        display_name=_(u"Open Date"),
        help=_(u"Stage open date"),
        scope=Scope.settings
    )

    close_date = DateTime(
        display_name=_(u"Close Date"),
        help=_(u"Stage close date"),
        scope=Scope.settings
    )

    STAGE_WRAPPER_TEMPLATE = 'templates/html/stages/stage_wrapper.html'

    editable_fields = ('display_name', 'open_date', 'close_date')
    has_children = True
    has_score = False  # TODO: Group project V1 are graded at activity level. Check if we need to follow that

    COMMON_ALLOWED_BLOCKS = OrderedDict([
        ("html", _(u"HTML")),
        (GroupProjectResourceXBlock.CATEGORY, _(u"Resource"))
    ])
    STAGE_SPECIFIC_ALLOWED_BLOCKS = {}

    @property
    def id(self):
        return self.scope_ids.usage_id

    @lazy
    def allowed_nested_blocks(self):
        blocks = OrderedDict()
        blocks.update(self.COMMON_ALLOWED_BLOCKS)
        blocks.update(self.STAGE_SPECIFIC_ALLOWED_BLOCKS)
        return blocks

    @lazy
    def activity(self):
        return self.get_parent()

    @property
    def resources(self):
        return self._get_children_by_category(GroupProjectResourceXBlock.CATEGORY)

    @property
    def grading_criteria(self):
        return (resource for resource in self.resources if resource.grading_criteria)

    @property
    def formatted_open_date(self):
        return format_date(self.open_date)

    @property
    def formatted_close_date(self):
        return format_date(self.close_date)

    @property
    def is_open(self):
        return (self.open_date is None) or (self.open_date <= datetime.utcnow().replace(tzinfo=pytz.UTC))

    @property
    def is_closed(self):
        # If this stage is being loaded for the purposes of a TA grading,
        # then we never close the stage - in this way a TA can impose any
        # action necessary even if it has been closed to the group members
        if self.activity.is_admin_grader:
            return False

        return (self.close_date is not None) and (self.close_date < datetime.utcnow().replace(tzinfo=pytz.UTC))

    def student_view(self, context):
        stage_fragment = self.get_stage_content_fragment(context)

        fragment = Fragment()
        fragment.add_frag_resources(stage_fragment)
        render_context = {
            'stage': self, 'stage_content': stage_fragment.content,
            "ta_graded": self.activity.group_reviews_required_count
        }
        fragment.add_content(loader.render_template(self.STAGE_WRAPPER_TEMPLATE, render_context))

        return fragment

    def get_stage_content_fragment(self, context):
        return self.get_children_fragment(context)

    def author_preview_view(self, context):
        return self.student_view(context)

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

    def mark_complete(self, user_id):
        try:
            project_api.mark_as_complete(self.activity.course_id, self.activity.content_id, user_id, self.id)
        except ApiError as e:
            # 409 indicates that the completion record already existed # That's ok in this case
            if e.code != 409:
                raise

    def get_stage_state(self):
        """
        Gets stage completion state
        """
        users_in_group, completed_users = project_api.get_stage_state(
            self.activity.course_id,
            self.activity.id,
            self.activity.user_id,
            self.id
        )

        if not users_in_group or not completed_users:
            return StageState.NOT_STARTED
        if users_in_group <= completed_users:
            return StageState.COMPLETED
        if users_in_group & completed_users:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def navigation_view(self, context):
        fragment = Fragment()
        rendering_context = {
            'stage': self,
            'activity_id': self.activity.id,
            'stage_state': self.get_stage_state()
        }
        rendering_context.update(context)
        fragment.add_content(loader.render_template("templates/html/stages/navigation_view.html", rendering_context))
        return fragment

    def resources_view(self, context):
        fragment = Fragment()

        resource_contents = []
        for resource in self.resources:
            resource_fragment = resource.render('resources_view', context)
            fragment.add_frag_resources(resource_fragment)
            resource_contents.append(resource_fragment.content)

        context = {'stage': self, 'resource_contents': resource_contents}
        fragment.add_content(loader.render_template("templates/html/stages/resources_view.html", context))

        return fragment


class BasicStage(BaseGroupActivityStage):
    type = u'Text'
    CATEGORY = 'group-project-v2-stage-basic'


class SubmissionStage(BaseGroupActivityStage):
    type = u'Task'
    CATEGORY = 'group-project-v2-stage-submission'

    submissions_stage = True
    STAGE_SPECIFIC_ALLOWED_BLOCKS = OrderedDict([
        (GroupProjectSubmissionXBlock.CATEGORY, _(u"Submission"))
    ])

    @property
    def submissions(self):
        return self._get_children_by_category(GroupProjectSubmissionXBlock.CATEGORY)

    @property
    def is_upload_available(self):
        return self.submissions and self.is_open and not self.is_closed

    @property
    def has_submissions(self):
        return bool(self.submissions)  # explicitly converting to bool to indicate that it is bool property

    def validate(self):
        violations = super(SubmissionStage, self).validate()

        if not self.submissions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Submissions are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations

    @property
    def has_all_submissions(self):
        return all(submission.upload is not None for submission in self.submissions)

    def submissions_view(self, context):
        fragment = Fragment()

        submission_contents = []
        for resource in self.submissions:
            resource_fragment = resource.render('submissions_view', context)
            fragment.add_frag_resources(resource_fragment)
            submission_contents.append(resource_fragment.content)

        context = {'stage': self, 'submission_contents': submission_contents}
        fragment.add_content(loader.render_template("templates/html/stages/submissions_view.html", context))

        return fragment


class ReviewBaseStage(BaseGroupActivityStage):
    type = u'Grade'
    STAGE_SPECIFIC_ALLOWED_BLOCKS = {GroupProjectReviewQuestionXBlock.CATEGORY: _(u"Review Question")}

    @property
    def questions(self):
        return self._get_children_by_category(GroupProjectReviewQuestionXBlock.CATEGORY)

    @property
    def grade_questions(self):
        return (question for question in self._questions if question.grade)

    @property
    def grade_header_html(self):
        return inner_html(self._grade_header)

    def validate(self):
        violations = super(ReviewBaseStage, self).validate()

        if not self.questions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Questions are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations


class PeerReviewStage(ReviewBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_review.html'
    CATEGORY = 'group-project-v2-stage-peer-review'


class GroupReviewStage(ReviewBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/group_review.html'
    CATEGORY = 'group-project-v2-stage-group-review'

    @XBlock.handler
    def other_submission_links(self, request, suffix=''):
        pass
        # group_id = request.GET["group_id"]
        #
        # self.update_submission_data(group_id)
        # context = {'submissions': self.submissions}
        # html_output = loader.render_template('/templates/html/review_submissions.html', context)
        #
        # return webob.response.Response(body=json.dumps({"html": html_output}))


class AssessmentBaseStage(BaseGroupActivityStage):
    type = u'Evaluation'
    HTML_TEMPLATE = 'templates/html/stages/peer_assessment.html'

    STAGE_SPECIFIC_ALLOWED_BLOCKS = OrderedDict([
        (GroupProjectReviewAssessmentXBlock.CATEGORY, _(u"Review Question"))
    ])

    @property
    def assessments(self):
        return self._get_children_by_category(GroupProjectReviewAssessmentXBlock.CATEGORY)

    def validate(self):
        violations = super(AssessmentBaseStage, self).validate()

        if not self.assessments:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Assessments are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations


class PeerAssessmentStage(AssessmentBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_assessment.html'
    CATEGORY = 'group-project-v2-stage-peer-assessment'


class GroupAssessmentStage(AssessmentBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/group_assessment.html'
    CATEGORY = 'group-project-v2-stage-group-assessment'


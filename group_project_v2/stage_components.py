from collections import namedtuple
import json
import logging
from xml.etree import ElementTree

from django.utils import html
from lazy.lazy import lazy
import webob
from xblock.core import XBlock
from xblock.fields import String, Boolean, Scope, UNIQUE_ID
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.studio_editable import StudioEditableXBlockMixin

from group_project_v2.api_error import ApiError
from group_project_v2.mixins import UserAwareXBlockMixin, WorkgroupAwareXBlockMixin, XBlockWithPreviewMixin
from group_project_v2.project_api import ProjectAPIXBlockMixin
from group_project_v2.project_navigator import ResourcesViewXBlock, SubmissionsViewXBlock
from group_project_v2.upload_file import UploadFile
from group_project_v2.utils import NO_EDITABLE_SETTINGS, get_link_to_block
from group_project_v2.utils import outer_html, gettext as _, loader, format_date, build_date_field, mean, \
    outsider_disallowed_protected_view

log = logging.getLogger(__name__)


class GroupProjectResourceXBlock(XBlock, StudioEditableXBlockMixin, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-resource"

    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/project_navigator/resource.html'

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

    def student_view(self, context):  # pylint: disable=unused-argument, no-self-use
        return Fragment()

    def author_view(self, context):
        return self.resources_view(context)

    def resources_view(self, context):
        fragment = Fragment()
        render_context = {'resource': self}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        return fragment


class StaticContentBaseXBlock(XBlock, XBlockWithPreviewMixin):
    TARGET_PROJECT_NAVIGATOR_VIEW = None
    TEXT_TEMPLATE = None

    @lazy
    def stage(self):
        return self.get_parent()

    def student_view(self, context):
        activity = self.stage.activity
        if activity.project.navigator is None:
            return Fragment()

        target_block = activity.project.navigator.get_child_of_category(self.TARGET_PROJECT_NAVIGATOR_VIEW)

        if target_block is None:
            return Fragment()

        render_context = {
            'block': self,
            'block_link': get_link_to_block(target_block),
            'block_text': self.TEXT_TEMPLATE.format(activity_name=activity.display_name),
            'target_block_id': str(target_block.scope_ids.usage_id),
            'view_icon': target_block.icon
        }
        render_context.update(context)

        fragment = Fragment()
        fragment.add_content(loader.render_template("templates/html/components/static_content.html", render_context))
        return fragment

    def studio_view(self):
        return Fragment(NO_EDITABLE_SETTINGS)


class SubmissionsStaticContentXBlock(StaticContentBaseXBlock):
    DISPLAY_NAME = _(u"Submissions Help Text")
    CATEGORY = "gp-v2-static-submissions"

    display_name_with_default = DISPLAY_NAME

    TARGET_PROJECT_NAVIGATOR_VIEW = SubmissionsViewXBlock.CATEGORY
    TEXT_TEMPLATE = "You can upload (or replace) your file(s) before the due date in the project navigator panel" \
                    " at right by clicking the upload button"


class GradeRubricStaticContentXBlock(StaticContentBaseXBlock):
    DISPLAY_NAME = _(u"Grade Rubric Help Text")
    CATEGORY = "gp-v2-static-grade-rubric"

    display_name_with_default = DISPLAY_NAME

    TARGET_PROJECT_NAVIGATOR_VIEW = ResourcesViewXBlock.CATEGORY
    TEXT_TEMPLATE = "The {activity_name} grading rubric is provided in the project navigator panel" \
                    " at right by clicking the resources button"""


# pylint: disable=invalid-name
SubmissionUpload = namedtuple("SubmissionUpload", "location file_name submission_date user_details")


@XBlock.needs('user')
@XBlock.wants('notifications')
class GroupProjectSubmissionXBlock(XBlock, ProjectAPIXBlockMixin, StudioEditableXBlockMixin, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-submission"
    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/components/submission_navigator_view.html'
    REVIEW_VIEW_TEMPLATE = 'templates/html/components/submission_review_view.html'

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
        submission_map = self.project_api.get_latest_workgroup_submissions_by_id(group_id)
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

    def student_view(self, context):  # pylint: disable=unused-argument, no-self-use
        return Fragment()

    def submissions_view(self, context):
        fragment = Fragment()
        render_context = {'submission': self, 'upload': self.upload}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/submission.js'))
        fragment.initialize_js("GroupProjectSubmissionBlock")
        return fragment

    def submission_review_view(self, context):
        group_id = context.get('group_id', self.stage.activity.workgroup["id"])
        fragment = Fragment()
        render_context = {'submission': self, 'upload': self.get_upload(group_id)}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.REVIEW_VIEW_TEMPLATE, render_context))
        # NOTE: adding js/css likely won't work here, as the result of this view is added as an HTML to an existing DOM
        # element
        return fragment

    @XBlock.handler
    def upload_submission(self, request, suffix=''):  # pylint: disable=unused-argument
        """
        Handles submission upload and marks stage as completed if all submissions in stage have uploads.
        """
        if not self.stage.available_now:
            template = self.stage.STAGE_NOT_OPEN_MESSAGE if not self.stage.is_open else self.stage.STAGE_CLOSED_MESSAGE
            return {'result': 'error',  'msg': template.format(action=self.stage.STAGE_ACTION)}

        target_activity = self.stage.activity
        response_data = {"message": _("File(s) successfully submitted")}
        failure_code = 0
        try:
            context = {
                "user_id": target_activity.user_id,
                "group_id": target_activity.workgroup['id'],
                "project_api": self.project_api,
                "course_id": target_activity.course_id
            }

            uploaded_file = self.persist_and_submit_file(target_activity, context, request.params[self.upload_id].file)

            response_data["submissions"] = {uploaded_file.submission_id: uploaded_file.file_url}

            self.stage.check_submissions_and_mark_complete()
            response_data["new_stage_states"] = [self.stage.get_new_stage_state_data()]

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


class PeerSelectorXBlock(XBlock, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-peer-selector"
    display_name_with_default = _(u"Teammate selector XBlock")
    STUDENT_TEMPLATE = "templates/html/components/peer_selector.html"

    @property
    def stage(self):
        return self.get_parent()

    @property
    def peers(self):
        return self.stage.team_members

    def student_view(self, context):
        fragment = Fragment()
        render_context = {'selector': self, 'peers': self.peers}
        render_context.update(context)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/components/review_subject_selector.css"))
        fragment.add_content(loader.render_template(self.STUDENT_TEMPLATE, render_context))
        return fragment

    def author_view(self, context):
        fake_peers = [
            {"id": 1, "username": "Jack"},
            {"id": 2, "username": "Jill"},
        ]
        render_context = {
            'demo': True,
            'peers': fake_peers
        }
        render_context.update(context)
        return self.student_view(render_context)

    def studio_view(self, context):  # pylint: disable=unused-argument, no-self-use
        fragment = Fragment()
        fragment.add_content(NO_EDITABLE_SETTINGS)
        return fragment


class GroupSelectorXBlock(XBlock, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-group-selector"
    display_name_with_default = _(u"Group selector XBlock")
    STUDENT_TEMPLATE = "templates/html/components/group_selector.html"

    @property
    def stage(self):
        return self.get_parent()

    @property
    def groups(self):
        return self.stage.review_groups

    def student_view(self, context):
        fragment = Fragment()
        render_context = {'selector': self, 'groups': self.groups}
        render_context.update(context)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/components/review_subject_selector.css"))
        fragment.add_content(loader.render_template(self.STUDENT_TEMPLATE, render_context))
        return fragment

    def author_view(self, context):
        fake_groups = [
            {"id": 1},
            {"id": 2},
        ]
        render_context = {
            'demo': True,
            'groups': fake_groups
        }
        render_context.update(context)
        return self.student_view(render_context)

    def studio_view(self, context):  # pylint: disable=unused-argument, no-self-use
        fragment = Fragment()
        fragment.add_content(NO_EDITABLE_SETTINGS)
        return fragment


class GroupProjectReviewQuestionXBlock(XBlock, StudioEditableXBlockMixin, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-review-question"

    @property
    def display_name_with_default(self):
        return _(u"Review Question {title}").format(title=self.title)

    question_id = String(
        display_name=_(u"Question ID"),
        default=UNIQUE_ID,
        scope=Scope.content
    )

    title = String(
        display_name=_(u"Question text"),
        default="",
        scope=Scope.content
    )

    # Label could be an HTML child XBlock, content could be a XBlock encapsulating HTML input/select/textarea
    # unfortunately, there aren't any XBlocks for HTML controls, hence reusing GP V1 approach
    assessment_title = String(
        display_name=_(u"Assessment question text"),
        help=_(u"Overrides question title when displayed in assessment mode"),
        default=None,
        scope=Scope.content
    )

    question_content = String(
        display_name=_(u"Question content"),
        help=_(u"HTML control"),
        default="",
        scope=Scope.content,
        multiline_editor="xml"
    )

    required = Boolean(
        display_name=_(u"Required"),
        default=False,
        scope=Scope.content
    )

    grade = Boolean(
        display_name=_(u"Grading"),
        help=_(u"IF True, answers to this question will be used to calculate student grade for Group Project."),
        default=False,
        scope=Scope.content
    )

    single_line = Boolean(
        display_name=_(u"Single line"),
        help=_(u"If True question label and content will be displayed on single line, allowing for more compact layout."
               u"Only affects presentation."),
        default=False,
        scope=Scope.content
    )

    question_css_classes = String(
        display_name=_(u"CSS classes"),
        help=_(u"CSS classes to be set on question element. Only affects presentation."),
        scope=Scope.content
    )

    editable_fields = (
        "question_id", "title", "assessment_title", "question_content", "required", "grade", "single_line",
        "question_css_classes"
    )
    has_author_view = True

    @lazy
    def stage(self):
        return self.get_parent()

    def render_content(self):
        try:
            answer_node = ElementTree.fromstring(self.question_content)
        except ElementTree.ParseError as exception:
            log.exception(exception)
            return ""

        answer_node.set('name', self.question_id)
        answer_node.set('id', self.question_id)
        current_class = answer_node.get('class')
        answer_classes = ['answer']
        if current_class:
            answer_classes.append(current_class)
        if self.single_line:
            answer_classes.append('side')
        if self.stage.is_closed:
            answer_node.set('disabled', 'disabled')
        else:
            answer_classes.append('editable')
        answer_node.set('class', ' '.join(answer_classes))

        return outer_html(answer_node)

    def student_view(self, context):
        question_classes = ["question"]
        if self.required:
            question_classes.append("required")
        if self.question_css_classes:
            question_classes.append(self.question_css_classes)

        fragment = Fragment()
        render_context = {
            'question': self,
            'question_classes': " ".join(question_classes),
            'question_content': self.render_content()
        }
        render_context.update(context)
        fragment.add_content(loader.render_template("templates/html/components/review_question.html", render_context))
        return fragment

    def studio_view(self, context):
        fragment = super(GroupProjectReviewQuestionXBlock, self).studio_view(context)

        # TODO: StudioEditableXBlockMixin should really support Codemirror XML editor
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/question_edit.css"))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, "public/js/question_edit.js"))
        fragment.initialize_js("GroupProjectQuestionEdit")
        return fragment

    def author_view(self, context):
        fragment = self.student_view(context)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/question_edit.css"))
        return fragment


class GroupProjectBaseAssessmentXBlock(
    XBlock, ProjectAPIXBlockMixin, StudioEditableXBlockMixin, XBlockWithPreviewMixin
):
    question_id = String(
        display_name=_(u"Question"),
        help=_(u"Question to be assessed"),
        scope=Scope.content
    )

    show_mean = Boolean(
        display_name=_(u"Show mean value"),
        help=_(u"If True, converts review answers to numbers and calculates mean value"),
        default=False,
        scope=Scope.content
    )

    editable_fields = ("question_id", "show_mean")
    has_author_view = True

    @property
    def display_name_with_default(self):
        if self.question:
            return _(u'Review Assessment for question "{question_title}"').format(question_title=self.question.title)
        else:
            return _(u"Review Assessment")

    @lazy
    def stage(self):
        return self.get_parent()

    @lazy
    def question(self):
        matching_questions = [
            question for question in self.stage.activity.questions if question.question_id == self.question_id
        ]
        if len(matching_questions) > 1:
            raise ValueError("Question ID is not unique")
        if not matching_questions:
            return None

        return matching_questions[0]

    @outsider_disallowed_protected_view
    def student_view(self, context):
        if self.question is None:
            raise ValueError("No question selected")

        raw_feedback = self.get_feedback()

        feedback = []
        for item in raw_feedback:
            feedback.append(html.escape(item['answer']))

        fragment = Fragment()
        title = self.question.assessment_title if self.question.assessment_title else self.question.title
        render_context = {'assessment': self, 'question_title': title, 'feedback': feedback}
        if self.show_mean:
            try:
                render_context['mean'] = "{0:.1f}".format(mean(feedback))
            except ValueError as exc:
                log.warn(exc)
                render_context['mean'] = None

        render_context.update(context)
        fragment.add_content(loader.render_template("templates/html/components/review_assessment.html", render_context))
        return fragment

    def validate(self):
        validation = super(GroupProjectBaseAssessmentXBlock, self).validate()

        if self.question is None:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"No question selected")
            ))

        return validation

    def author_view(self, context):
        if self.question:
            return self.student_view(context)

        fragment = Fragment()
        fragment.add_content(_(u"Question is not selected"))
        return fragment


class GroupProjectPeerAssessmentXBlock(
    GroupProjectBaseAssessmentXBlock, UserAwareXBlockMixin, WorkgroupAwareXBlockMixin, XBlockWithPreviewMixin
):
    CATEGORY = "gp-v2-peer-assessment"

    def get_feedback(self):
        all_feedback = self.project_api.get_user_peer_review_items(
            self.user_id,
            self.workgroup['id'],
            self.stage.content_id,
        )

        return [item for item in all_feedback if item["question"] == self.question_id]


class GroupProjectGroupAssessmentXBlock(
    GroupProjectBaseAssessmentXBlock, UserAwareXBlockMixin, WorkgroupAwareXBlockMixin, XBlockWithPreviewMixin
):
    CATEGORY = "gp-v2-group-assessment"

    def get_feedback(self):
        all_feedback = self.project_api.get_workgroup_review_items_for_group(
            self.workgroup['id'],
            self.stage.content_id,
        )
        return [item for item in all_feedback if item["question"] == self.question_id]

from builtins import str
import json
import logging
from collections import namedtuple
from xml.etree import ElementTree

import webob
from datetime import date

from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import html
from lazy.lazy import lazy
from upload_validator import FileTypeValidator
from xblock.core import XBlock
from xblock.fields import String, Boolean, Scope, UNIQUE_ID
from xblock.validation import ValidationMessage
from web_fragments.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin, XBlockWithPreviewMixin

from group_project_v2 import messages
from group_project_v2.api_error import ApiError
from group_project_v2.mixins import (
    CompletionMixin,
    NoStudioEditableSettingsMixin,
    UserAwareXBlockMixin,
    WorkgroupAwareXBlockMixin,
)
from group_project_v2.project_api import ProjectAPIXBlockMixin
from group_project_v2.project_navigator import ResourcesViewXBlock, SubmissionsViewXBlock
from group_project_v2.upload_file import UploadFile
from group_project_v2.messages import UNKNOWN_ERROR
from group_project_v2.utils import (
    FieldValuesContextManager,
    MUST_BE_OVERRIDDEN,
    add_resource,
    get_link_to_block,
    make_user_caption,
    make_s3_link_temporary,
)
from group_project_v2.utils import (
    build_date_field,
    format_date,
    gettext as _,
    groupwork_protected_view,
    loader,
    mean,
    outer_html,
)

log = logging.getLogger(__name__)


class BaseStageComponentXBlock(CompletionMixin, XBlock):
    @lazy
    def stage(self):
        """
        :rtype: group_project_v2.stage.base.BaseGroupActivityStage
        """
        return self.get_parent()


class BaseGroupProjectResourceXBlock(BaseStageComponentXBlock, StudioEditableXBlockMixin, XBlockWithPreviewMixin):
    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the resource"),
        scope=Scope.settings,
        default=_(u"Group Project V2 Resource")
    )

    description = String(
        display_name=_(u"Resource Description"),
        scope=Scope.settings
    )

    editable_fields = ('display_name', 'description')

    def student_view(self, _context):  # pylint: disable=no-self-use
        return Fragment()

    def resources_view(self, context):
        fragment = Fragment()
        render_context = {'resource': self}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        return fragment


class GroupProjectResourceXBlock(BaseGroupProjectResourceXBlock):
    CATEGORY = "gp-v2-resource"
    STUDIO_LABEL = _(u"Resource")

    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/components/resource.html'

    resource_location = String(
        display_name=_(u"Resource Location"),
        help=_(u"A url to download/view the resource"),
        scope=Scope.settings,
    )

    grading_criteria = Boolean(
        display_name=_(u"Grading Criteria?"),
        help=_(u"If true, resource will be treated as grading criteria"),
        scope=Scope.settings,
        default=False
    )

    editable_fields = ('display_name', 'description', 'resource_location', )

    def author_view(self, context):
        return self.resources_view(context)


class GroupProjectVideoResourceXBlock(BaseGroupProjectResourceXBlock):
    CATEGORY = "gp-v2-video-resource"
    STUDIO_LABEL = _(u"Video Resource")
    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/components/video_resource.html'

    video_id = String(
        display_name=_(u"Ooyala/Brightcove content ID"),
        help=_(u"This is the Ooyala/Brightcove Content Identifier"),
        default="Q1eXg5NzpKqUUzBm5WTIb6bXuiWHrRMi",
        scope=Scope.content,
    )

    editable_fields = ('display_name', 'description', 'video_id')

    @classmethod
    def is_available(cls):
        return True  # TODO: restore conditional availability when switched to use actual Ooyala XBlock

    @classmethod
    def brightcove_account_id(cls):
        """
        Gets bcove account id from settings
        """
        xblock_settings = settings.XBLOCK_SETTINGS if hasattr(settings, "XBLOCK_SETTINGS") else {}
        return xblock_settings.get('OoyalaPlayerBlock', {}).get('BCOVE_ACCOUNT_ID')

    @property
    def video_type(self):
        """
        Checks if video_id belongs to Brightcove or Ooyala
        """
        try:
            # Brightcove IDs are numeric
            int(self.video_id)
            return 'brightcove'
        except (ValueError, TypeError):
            return 'ooyala'

    def resources_view(self, context):
        render_context = {
            'video_id': self.video_id,
            'player_type': self.video_type,
            'bc_account_id': self.brightcove_account_id(),
        }
        render_context.update(context)
        fragment = super(GroupProjectVideoResourceXBlock, self).resources_view(render_context)
        fragment.add_javascript_url(url='//players.brightcove.net/{}/default_default/index.min.js'
                                    .format(self.brightcove_account_id()))
        return fragment

    def author_view(self, context):
        return self.resources_view(context)

    def validate_field_data(self, validation, data):
        if not data.video_id:
            validation.add(ValidationMessage(ValidationMessage.ERROR, messages.MUST_CONTAIN_CONTENT_ID))

        return validation


class StaticContentBaseXBlock(BaseStageComponentXBlock, XBlockWithPreviewMixin, NoStudioEditableSettingsMixin):
    TARGET_PROJECT_NAVIGATOR_VIEW = None
    TEXT_TEMPLATE = None
    TEMPLATE_PATH = "templates/html/components/static_content.html"

    def student_view(self, context):
        try:
            activity = self.stage.activity
            target_block = activity.project.navigator.get_child_of_category(self.TARGET_PROJECT_NAVIGATOR_VIEW)
        except AttributeError:
            activity = None
            target_block = None

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
        fragment.add_content(loader.render_template(self.TEMPLATE_PATH, render_context))
        return fragment


class SubmissionsStaticContentXBlock(StaticContentBaseXBlock):
    DISPLAY_NAME = _(u"Submissions Help Text")
    STUDIO_LABEL = DISPLAY_NAME
    CATEGORY = "gp-v2-static-submissions"

    display_name_with_default = DISPLAY_NAME

    TARGET_PROJECT_NAVIGATOR_VIEW = SubmissionsViewXBlock.CATEGORY
    TEXT_TEMPLATE = "You can upload (or replace) your file(s) before the due date in the project navigator panel" \
                    " at right by clicking the upload button"


class GradeRubricStaticContentXBlock(StaticContentBaseXBlock):
    DISPLAY_NAME = _(u"Grade Rubric Help Text")
    STUDIO_LABEL = DISPLAY_NAME
    CATEGORY = "gp-v2-static-grade-rubric"

    display_name_with_default = DISPLAY_NAME

    TARGET_PROJECT_NAVIGATOR_VIEW = ResourcesViewXBlock.CATEGORY
    TEXT_TEMPLATE = "The {activity_name} grading rubric is provided in the project navigator panel" \
                    " at right by clicking the resources button"""


# pylint: disable=invalid-name
SubmissionUpload = namedtuple("SubmissionUpload", "location file_name submission_date user_details")


@XBlock.needs('user')
@XBlock.wants('notifications')
class GroupProjectSubmissionXBlock(
        BaseStageComponentXBlock, ProjectAPIXBlockMixin, StudioEditableXBlockMixin, XBlockWithPreviewMixin
):
    CATEGORY = "gp-v2-submission"
    STUDIO_LABEL = _(u"Submission")
    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/components/submission_navigator_view.html'
    REVIEW_VIEW_TEMPLATE = 'templates/html/components/submission_review_view.html'

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the submission"),
        scope=Scope.settings,
        default=_(u"Group Project V2 Submission")
    )

    description = String(
        display_name=_(u"Submission Description"),
        scope=Scope.settings
    )

    upload_id = String(
        display_name=_(u"Upload ID"),
        help=_(U"This string is used as an identifier for an upload. "
               U"Submissions sharing the same Upload ID will be updated simultaneously"),
    )

    editable_fields = ('display_name', 'description', 'upload_id')

    SUBMISSION_RECEIVED_EVENT = "activity.received_submission"

    # TODO: Make configurable via XBlock settings
    DEFAULT_FILE_FILTERS = {
        "mime-types": (
            # Images
            "image/png", "image/jpeg", "image/tiff",
            # Excel
            "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            # Word
            "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            # PowerPoint
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            # PDF
            "application/pdf"
        ),
        "extensions": ("png", "jpg", "jpeg", "tif", "tiff", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf",)
    }

    validator = FileTypeValidator(
        allowed_types=DEFAULT_FILE_FILTERS["mime-types"],
        allowed_extensions=[".{}".format(ext) for ext in DEFAULT_FILE_FILTERS["extensions"]]
    )

    def get_upload(self, group_id):
        submission_map = self.project_api.get_latest_workgroup_submissions_by_id(group_id)
        submission_data = submission_map.get(self.upload_id, None)

        if submission_data is None:
            return None

        document_signed_url = make_s3_link_temporary(
            submission_data.get('workgroup'),
            submission_data['document_url'].split('/')[-2],
            submission_data['document_filename'],
            submission_data["document_url"]
        )

        return SubmissionUpload(
            document_signed_url,
            submission_data["document_filename"],
            format_date(build_date_field(submission_data["modified"])),
            submission_data.get("user_details", None)
        )

    @property
    def upload(self):
        return self.get_upload(self.stage.activity.workgroup.id)

    def student_view(self, _context):  # pylint: disable=no-self-use
        return Fragment()

    def submissions_view(self, context):
        fragment = Fragment()
        # pylint: disable=consider-using-ternary
        uploading_allowed = (self.stage.available_now and self.stage.is_group_member) or self.stage.is_admin_grader
        render_context = {'submission': self, 'upload': self.upload, 'disabled': not uploading_allowed}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        add_resource(self, 'javascript', 'public/js/components/submission.js', fragment)
        fragment.initialize_js("GroupProjectSubmissionBlock")
        return fragment

    def submission_review_view(self, context):
        group_id = context.get('group_id', self.stage.activity.workgroup.id)
        fragment = Fragment()
        render_context = {'submission': self, 'upload': self.get_upload(group_id)}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.REVIEW_VIEW_TEMPLATE, render_context))
        # NOTE: adding js/css likely won't work here, as the result of this view is added as an HTML to an existing DOM
        # element
        return fragment

    def _validate_upload(self, request):
        if not self.stage.available_now:
            template = messages.STAGE_NOT_OPEN_TEMPLATE if not self.stage.is_open else messages.STAGE_CLOSED_TEMPLATE
            # 422 = unprocessable entity
            return 422, {'result': 'error', 'message': template.format(action=self.stage.STAGE_ACTION)}

        if not self.stage.is_group_member and not self.stage.is_admin_grader:
            # 403 - forbidden
            return 403, {'result': 'error', 'message': messages.NON_GROUP_MEMBER_UPLOAD}

        try:
            self.validator(request.params[self.upload_id].file)
        except ValidationError as validationError:
            message = validationError.message % validationError.params
            # 400 - BAD REQUEST
            return 400, {'result': 'error', 'message': message}

        return None, None

    @XBlock.handler
    def upload_submission(self, request, _suffix=''):
        """
        Handles submission upload and marks stage as completed if all submissions in stage have uploads.
        :param request: HTTP request
        :param str _suffix:
        """
        failure_code, response_data = self._validate_upload(request)

        if failure_code is None and response_data is None:
            target_activity = self.stage.activity
            response_data = {
                "title": messages.SUCCESSFUL_UPLOAD_TITLE,
                "message": messages.SUCCESSFUL_UPLOAD_MESSAGE_TPL.format(icon='fa fa-paperclip')
            }
            failure_code = 0
            try:
                context = {
                    "user_id": target_activity.user_id,
                    "group_id": target_activity.workgroup.id,
                    "project_api": self.project_api,
                    "course_id": target_activity.course_id
                }

                uploaded_file = self.persist_and_submit_file(
                    target_activity, context, request.params[self.upload_id].file
                )

                response_data["submissions"] = {
                    uploaded_file.submission_id: make_s3_link_temporary(
                        uploaded_file.group_id,
                        uploaded_file.sha1,
                        uploaded_file.file.name,
                        uploaded_file.file_url,
                    )
                }

                self.stage.check_submissions_and_mark_complete()
                response_data["new_stage_states"] = [self.stage.get_new_stage_state_data()]

                response_data['user_label'] = self.project_api.get_user_details(target_activity.user_id).user_label
                response_data['submission_date'] = format_date(date.today())

            except Exception as exception:  # pylint: disable=broad-except
                log.exception(exception)
                failure_code = 500
                if isinstance(exception, ApiError):
                    failure_code = exception.code
                error_message = str(exception).strip()
                if error_message == '':
                    error_message = UNKNOWN_ERROR

                response_data.update({
                    "title": messages.FAILED_UPLOAD_TITLE,
                    "message": messages.FAILED_UPLOAD_MESSAGE_TPL.format(error_goes_here=error_message)
                })

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
                self.SUBMISSION_RECEIVED_EVENT,
                {
                    "submission_id": uploaded_file.submission_id,
                    "filename": uploaded_file.file.name,
                    "content_id": activity.content_id,
                    "group_id": activity.workgroup.id,
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
            self.stage.fire_file_upload_notification(notifications_service)

        return uploaded_file


class ReviewSubjectSeletorXBlockBase(BaseStageComponentXBlock, XBlockWithPreviewMixin, NoStudioEditableSettingsMixin):
    """
    Base class for review selector blocks
    """
    @property
    def review_subjects(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    @XBlock.handler
    def get_statuses(self, _request, _suffix=''):
        response_data = {
            review_subject.id: self.stage.get_review_state(review_subject.id)
            for review_subject in self.review_subjects
        }
        return webob.response.Response(body=json.dumps(response_data))

    def student_view(self, context):
        fragment = Fragment()
        render_context = {'selector': self, 'review_subjects': self.get_review_subject_repr()}
        render_context.update(context)
        add_resource(self, 'css', "public/css/components/review_subject_selector.css", fragment)
        add_resource(self, 'javascript', "public/js/components/review_subject_selector.js", fragment)
        fragment.add_content(loader.render_template(self.STUDENT_TEMPLATE, render_context))
        fragment.initialize_js('ReviewSubjectSelectorXBlock')
        return fragment


class PeerSelectorXBlock(ReviewSubjectSeletorXBlockBase, UserAwareXBlockMixin):
    CATEGORY = "gp-v2-peer-selector"
    STUDIO_LABEL = _(u"Teammate Selector")
    display_name_with_default = _(u"Teammate Selector XBlock")
    STUDENT_TEMPLATE = "templates/html/components/peer_selector.html"

    @property
    def review_subjects(self):
        return self.stage.team_members

    def get_review_subject_repr(self):
        return [
            {
                'id': peer.id,
                'username': peer.username,
                'user_label': make_user_caption(peer),
                'profile_image_url': peer.profile_image_url
            }
            for peer in self.review_subjects
        ]

    def author_view(self, context):
        fake_peers = [
            {"id": 1, "username": "Jack"},
            {"id": 2, "username": "Jill"},
        ]
        render_context = {
            'demo': True,
            'review_subjects': fake_peers
        }
        render_context.update(context)
        return self.student_view(render_context)


class GroupSelectorXBlock(ReviewSubjectSeletorXBlockBase):
    CATEGORY = "gp-v2-group-selector"
    STUDIO_LABEL = _(u"Group Selector")
    display_name_with_default = _(u"Group Selector XBlock")
    STUDENT_TEMPLATE = "templates/html/components/group_selector.html"

    @property
    def review_subjects(self):
        return self.stage.review_groups

    def get_review_subject_repr(self):
        return [{'id': group.id} for group in self.review_subjects]

    def author_view(self, context):
        fake_groups = [
            {"id": 1},
            {"id": 2},
        ]
        render_context = {
            'demo': True,
            'review_subjects': fake_groups
        }
        render_context.update(context)
        return self.student_view(render_context)


class GroupProjectReviewQuestionXBlock(BaseStageComponentXBlock, StudioEditableXBlockMixin, XBlockWithPreviewMixin):
    CATEGORY = "gp-v2-review-question"
    STUDIO_LABEL = _(u"Review Question")

    @property
    def display_name_with_default(self):
        return self.title or _(u"Review Question")

    question_id = String(
        display_name=_(u"Question ID"),
        default=UNIQUE_ID,
        scope=Scope.content,
        force_export=True
    )

    title = String(
        display_name=_(u"Question Text"),
        default=_(u""),
        scope=Scope.content
    )

    assessment_title = String(
        display_name=_(u"Assessment Question Text"),
        help=_(u"Overrides question title when displayed in assessment mode"),
        default=None,
        scope=Scope.content
    )

    question_content = String(
        display_name=_(u"Question Content"),
        help=_(u"HTML control"),
        default=_(u""),
        scope=Scope.content,
        multiline_editor="xml",
        xml_node=True
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
        display_name=_(u"Single Line"),
        help=_(u"If True question label and content will be displayed on single line, allowing for more compact layout."
               u"Only affects presentation."),
        default=False,
        scope=Scope.content
    )

    question_css_classes = String(
        display_name=_(u"CSS Classes"),
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
        except ElementTree.ParseError:
            message_tpl = "Exception when parsing question content for question {question_id}. Content is [{content}]."
            message_tpl.format(question_id=self.question_id, content=self.question_content)
            log.exception(message_tpl)
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
        fragment.add_content(
            loader.render_django_template("templates/html/components/review_question.html", render_context))
        return fragment

    def studio_view(self, context):
        fragment = super(GroupProjectReviewQuestionXBlock, self).studio_view(context)

        # TODO: StudioEditableXBlockMixin should really support Codemirror XML editor
        add_resource(self, 'css', "public/css/components/question_edit.css", fragment)
        add_resource(self, 'javascript', "public/js/components/question_edit.js", fragment)
        fragment.initialize_js("GroupProjectQuestionEdit")
        return fragment

    def author_view(self, context):
        fragment = self.student_view(context)
        add_resource(self, 'css', "public/css/components/question_edit.css", fragment)
        return fragment


class GroupProjectBaseFeedbackDisplayXBlock(
        BaseStageComponentXBlock, StudioEditableXBlockMixin, XBlockWithPreviewMixin, WorkgroupAwareXBlockMixin
):
    DEFAULT_QUESTION_ID_VALUE = None

    NO_QUESTION_SELECTED = _(u"No question selected")
    QUESTION_NOT_FOUND = _(u"Selected question not found")
    QUESTION_ID_IS_NOT_UNIQUE = _(u"Question ID is not unique")

    question_id = String(
        display_name=_(u"Question ID"),
        help=_(u"Question to be assessed"),
        scope=Scope.content,
        default=DEFAULT_QUESTION_ID_VALUE
    )

    show_mean = Boolean(
        display_name=_(u"Show Mean Value"),
        help=_(u"If True, converts review answers to numbers and calculates mean value"),
        default=False,
        scope=Scope.content
    )

    editable_fields = ("question_id", "show_mean")
    has_author_view = True

    @property
    def activity_questions(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    @property
    def display_name_with_default(self):
        if self.question:
            return _(u'Review Assessment for question "{question_title}"').format(question_title=self.question.title)
        return _(u"Review Assessment")

    @lazy
    def question(self):
        matching_questions = [
            question for question in self.activity_questions if question.question_id == self.question_id
        ]
        if len(matching_questions) > 1:
            raise ValueError(self.QUESTION_ID_IS_NOT_UNIQUE)
        if not matching_questions:
            return None

        return matching_questions[0]

    @groupwork_protected_view
    def student_view(self, context):
        if self.question is None:
            return Fragment(messages.COMPONENT_MISCONFIGURED)

        raw_feedback = self.get_feedback()

        feedback = []
        for item in raw_feedback:
            feedback.append(html.escape(item['answer']))

        fragment = Fragment()
        title = self.question.assessment_title if self.question.assessment_title else self.question.title
        render_context = {'assessment': self, 'question_title': title, 'feedback': feedback}
        if self.show_mean:
            try:
                if feedback:
                    render_context['mean'] = "{0:.1f}".format(mean(feedback))
                else:
                    render_context['mean'] = _(u"N/A")
            except ValueError as exc:
                log.warn(exc)  # pylint: disable=deprecated-method
                render_context['mean'] = _(u"N/A")

        render_context.update(context)
        fragment.add_content(loader.render_template("templates/html/components/review_assessment.html", render_context))
        return fragment

    def validate(self):
        validation = super(GroupProjectBaseFeedbackDisplayXBlock, self).validate()

        if not self.question_id:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                self.NO_QUESTION_SELECTED
            ))

        if self.question_id and self.question is None:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                self.QUESTION_NOT_FOUND
            ))

        return validation

    def author_view(self, context):
        if self.question:
            return self.student_view(context)

        fragment = Fragment()
        fragment.add_content(messages.QUESTION_NOT_SELECTED)
        return fragment

    def studio_view(self, context):
        # can't use values_provider as we need it to be bound to current block instance
        with FieldValuesContextManager(self, 'question_id', self.question_ids_values_provider):
            return super(GroupProjectBaseFeedbackDisplayXBlock, self).studio_view(context)

    def question_ids_values_provider(self):
        not_selected = {
            "display_name": _(u"--- Not selected ---"), "value": self.DEFAULT_QUESTION_ID_VALUE
        }
        question_values = [
            {"display_name": question.title, "value": question.question_id}
            for question in self.activity_questions
        ]
        return [not_selected] + question_values


class GroupProjectTeamEvaluationDisplayXBlock(GroupProjectBaseFeedbackDisplayXBlock):
    CATEGORY = "gp-v2-peer-assessment"
    STUDIO_LABEL = _(u"Team Evaluation Display")

    @property
    def activity_questions(self):
        return self.stage.activity.team_evaluation_questions

    def get_feedback(self):
        all_feedback = self.project_api.get_user_peer_review_items(
            self.user_id,
            self.group_id,
            self.stage.activity_content_id,
        )

        return [item for item in all_feedback if item["question"] == self.question_id]


class GroupProjectGradeEvaluationDisplayXBlock(GroupProjectBaseFeedbackDisplayXBlock):
    CATEGORY = "gp-v2-group-assessment"
    STUDIO_LABEL = _(u"Grade Evaluation Display")

    @property
    def activity_questions(self):
        return self.stage.activity.peer_review_questions

    def get_feedback(self):
        all_feedback = self.project_api.get_workgroup_review_items_for_group(
            self.group_id,
            self.stage.activity_content_id,
        )
        return [item for item in all_feedback if item["question"] == self.question_id]


class ProjectTeamXBlock(
        BaseStageComponentXBlock, XBlockWithPreviewMixin, NoStudioEditableSettingsMixin, StudioEditableXBlockMixin,
):
    CATEGORY = 'gp-v2-project-team'
    STUDIO_LABEL = _(u"Project Team")

    display_name_with_default = STUDIO_LABEL

    def student_view(self, context):
        fragment = Fragment()
        # Could be a TA not in the group.
        if self.stage.is_group_member:
            user_details = [self.stage.project_api.get_member_data(self.stage.user_id)]
        else:
            user_details = []
        render_context = {
            'team_members': user_details + self.stage.team_members,
            'course_id': self.stage.course_id,
            'group_id': self.stage.workgroup.id
        }
        render_context.update(context)

        fragment.add_content(loader.render_template("templates/html/components/project_team.html", render_context))
        add_resource(self, 'css', "public/css/components/project_team.css", fragment)
        add_resource(self, 'javascript', "public/js/components/project_team.js", fragment)
        fragment.initialize_js("ProjectTeamXBlock")
        return fragment

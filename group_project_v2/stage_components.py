from collections import namedtuple
import copy
import json
from lazy.lazy import lazy
import logging
import xml.etree.ElementTree as ET
import webob

from xblock.core import XBlock
from xblock.fields import String, UNIQUE_ID, Boolean, Scope
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin

from group_project_v2.api_error import ApiError
from group_project_v2.project_api import project_api
from group_project_v2.upload_file import UploadFile

from group_project_v2.utils import outer_html, inner_html, gettext as _, loader, format_date, build_date_field


log = logging.getLogger(__name__)
NO_EDITABLE_SETTINGS = _(u"This XBlock does not contain any editable settigns")


class GroupProjectReviewQuestionXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-review-question"

    @property
    def display_name_with_default(self):
        return _(u"Review Question {question_id}").format(question_id=self.question_id)

    question_id = String(
        display_name=_(u"Question ID"),
        default=UNIQUE_ID
    )

    # Label could be an HTML child XBlock, content could be a XBlock encapsulating HTML input/select/textarea
    # unfortunately, there aren't any XBlocks for HTML controls, hence reusing GP V1 approach
    question_label = String(
        display_name=_(u"Question label"),
        default="",
        multiline_editor="html"
    )

    question_content = String(
        display_name=_(u"Question content"),
        help=_(u"HTML control"),
        default="",
        multiline_editor="xml"
    )

    required = Boolean(
        display_name=_(u"Required"),
        default=False
    )

    grade = Boolean(
        display_name=_(u"Grading"),
        help=_(u"IF True, answers to this question will be used to calculate student grade for Group Project."),
        default=False
    )

    single_line = Boolean(
        display_name=_(u"Single line"),
        help=_(u"If True question label and content will be displayed on single line, allowing for more compact layout."
               u"Only affects presentation."),
        default=False
    )

    question_css_classes = String(
        display_name=_(u"CSS classes"),
        help=_(u"CSS classes to be set on question element. Only affects presentation.")
    )

    editable_fields = (
        "question_id", "question_label", "question_content", "required", "grade", "single_line", "question_css_classes"
    )

    @lazy
    def stage(self):
        return self.get_parent()

    def render_label(self):
        try:
            label_node = ET.fromstring(self.question_label)
        except ET.ParseError as exception:
            log.exception(exception)
            return ""

        if len(inner_html(label_node)) > 0:
            label_node.set('for', self.question_id)
            current_class = label_node.get('class')
            label_classes = ['prompt']
            if current_class:
                label_classes.append(current_class)
            if self.single_line:
                label_classes.append('side')
            label_node.set('class', ' '.join(label_classes))
        return outer_html(label_node)

    def render_content(self):
        try:
            answer_node = ET.fromstring(self.question_content)
        except ET.ParseError as exception:
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
        context = {
            "question_classes": " ".join(question_classes),
            "question_label": self.render_label(),
            "question_content": self.render_content
        }
        fragment.add_content(loader.render_template("templates/html/components/review_question.html", context))
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


class GroupProjectReviewAssessmentXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-review-assessment"

class GroupActivityQuestion(object):
    def __init__(self, doc_tree, stage):

        self.id = doc_tree.get("id")  # pylint: disable=invalid-name
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")
        self.stage = stage
        self.required = (doc_tree.get("required", "true") == "true")
        designer_class = doc_tree.get("class")
        self.question_classes = ["question"]
        self.grade = doc_tree.get("grade") == "true"

        if self.required:
            self.question_classes.append("required")
        if designer_class:
            self.question_classes.append(designer_class)

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        current_class = answer_node.get('class')
        answer_classes = ['answer']
        if current_class:
            answer_classes.append(current_class)
        if self.small:
            answer_classes.append('side')
        if self.stage.is_closed:
            answer_node.set('disabled', 'disabled')
        else:
            answer_classes.append('editable')
        answer_node.set('class', ' '.join(answer_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        label_html = ''
        label_node = copy.deepcopy(self.label)
        if len(inner_html(label_node)) > 0:
            label_node.set('for', self.id)
            current_class = label_node.get('class')
            label_classes = ['prompt']
            if current_class:
                label_classes.append(current_class)
            if self.small:
                label_classes.append('side')
            label_node.set('class', ' '.join(label_classes))
            label_html = outer_html(label_node)

        return '<div class="{}">{}{}</div>'.format(
            ' '.join(self.question_classes),
            label_html,
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html


class GroupActivityAssessment(object):
    def __init__(self, doc_tree):

        self.id = doc_tree.get("id")  # pylint: disable=invalid-name
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        answer_classes = ['answer']
        if self.small:
            answer_classes.append('side')
        current_class = answer_node.get('class')
        if current_class:
            answer_classes.append(current_class)
        answer_node.set('class', ' '.join(answer_classes))

        label_node = copy.deepcopy(self.label)
        label_node.set('for', self.id)
        current_class = label_node.get('class')
        label_classes = ['prompt']
        if current_class:
            label_classes.append(current_class)
        if self.small:
            label_classes.append('side')
        label_node.set('class', ' '.join(label_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        return "{}{}".format(
            outer_html(label_node),
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html


class PeerSelectorXBlock(XBlock):
    CATEGORY = "group-project-v2-peer-selector"
    display_name_with_default = _(u"Teammate selector XBlock")
    STUDENT_TEMPLATE = "templates/html/components/peer_selector.html"

    @property
    def stage(self):
        return self.get_parent()

    @property
    def peers(self):
        return self.stage.activity.team_members

    def student_view(self, context):
        fragment = Fragment()
        render_context = {'selector': self, 'peers': self.peers}
        render_context.update(context)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/components/peer_selector.css"))
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
        return self.student_view(render_context)

    def studio_view(self, context):
        fragment = Fragment()
        fragment.add_content(NO_EDITABLE_SETTINGS)
        return fragment


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


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'
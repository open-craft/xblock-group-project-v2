from collections import OrderedDict
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
from group_project_v2.mixins import (
    ChildrenNavigationXBlockMixin,
    WorkgroupAwareXBlockMixin, XBlockWithComponentsMixin, XBlockWithPreviewMixin,
    XBlockWithUrlNameDisplayMixin, AdminAccessControlXBlockMixin
)
from group_project_v2.notifications import StageNotificationsMixin
from group_project_v2.stage_components import (
    PeerSelectorXBlock, GroupSelectorXBlock,
    GroupProjectReviewQuestionXBlock, GroupProjectTeamEvaluationDisplayXBlock, GroupProjectGradeEvaluationDisplayXBlock,
    GroupProjectResourceXBlock, GroupProjectSubmissionXBlock, SubmissionsStaticContentXBlock,
    GradeRubricStaticContentXBlock, GroupProjectVideoResourceXBlock
)
from group_project_v2.utils import (
    loader, format_date, gettext as _, make_key, outsider_disallowed_protected_view,
    outsider_disallowed_protected_handler, key_error_protected_handler,
    get_link_to_block)

log = logging.getLogger(__name__)


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


class ReviewState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


class BaseGroupActivityStage(
    XBlockWithPreviewMixin, XBlockWithComponentsMixin, StageNotificationsMixin,
    XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin,
    ChildrenNavigationXBlockMixin, XBlockWithUrlNameDisplayMixin,
    WorkgroupAwareXBlockMixin, AdminAccessControlXBlockMixin
):
    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the stage"),
        scope=Scope.content,
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

    hide_stage_label = Boolean(
        display_name=_(u"Hide stage type label"),
        help=_(u"If true, hides stage type label in Project Navigator"),
        scope=Scope.settings,
        default=False
    )

    editable_fields = ('display_name', 'open_date', 'close_date', 'hide_stage_label')
    has_children = True
    has_score = False  # TODO: Group project V1 are graded at activity level. Check if we need to follow that
    submissions_stage = False

    CATEGORY = None
    STAGE_WRAPPER_TEMPLATE = 'templates/html/stages/stage_wrapper.html'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/default_view.html'

    NAVIGATION_LABEL = None
    STUDIO_LABEL = _(u"Stage")

    js_file = None
    js_init = None

    STAGE_NOT_OPEN_TEMPLATE = _(u"Can't {action} as it's not yet opened")
    STAGE_CLOSED_TEMPLATE = _(u"Can't {action} as it's closed")
    STAGE_URL_NAME_TEMPLATE = _(u"url_name to link to this {stage_name}:")

    CURRENT_STAGE_ID_PARAMETER_NAME = 'current_stage_id'

    @property
    def id(self):
        return self.scope_ids.usage_id

    @property
    def display_name_with_default(self):
        return u"{type_name} - {stage_name}".format(type_name=self.STUDIO_LABEL, stage_name=self.display_name)

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        """
        This property outputs an ordered dictionary of allowed nested XBlocks in form of block_category: block_caption.
        """
        blocks = OrderedDict([
            ("html", _(u"HTML")),
            (GroupProjectResourceXBlock.CATEGORY, GroupProjectResourceXBlock.STUDIO_LABEL)
        ])
        if GroupProjectVideoResourceXBlock.is_available():
            blocks.update(OrderedDict([
                (GroupProjectVideoResourceXBlock.CATEGORY, GroupProjectVideoResourceXBlock.STUDIO_LABEL)
            ]))
        return blocks

    @lazy
    def activity(self):
        return self.get_parent()

    @property
    def allow_admin_grader_access(self):
        return False

    @property
    def content_id(self):
        return self.activity.content_id

    @property
    def resources(self):
        return self._get_children_by_category(
            GroupProjectResourceXBlock.CATEGORY, GroupProjectVideoResourceXBlock.CATEGORY
        )

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
        if not self.is_group_member:
            return False

        return (self.close_date is not None) and (self.close_date < datetime.utcnow().replace(tzinfo=pytz.UTC))

    @property
    def completed(self):
        return self.get_stage_state() == StageState.COMPLETED

    @property
    def available_now(self):
        return self.is_open and not self.is_closed

    @property
    def url_name_caption(self):
        return self.STAGE_URL_NAME_TEMPLATE.format(stage_name=self.STUDIO_LABEL)

    def is_current_stage(self, context):
        return context.get(self.CURRENT_STAGE_ID_PARAMETER_NAME, None) == str(self.id)

    def _view_render(self, context, view='student_view'):
        stage_fragment = self.get_stage_content_fragment(context, view)

        fragment = Fragment()
        fragment.add_frag_resources(stage_fragment)
        render_context = {
            'stage': self, 'stage_content': stage_fragment.content,
            "ta_graded": self.activity.group_reviews_required_count
        }
        fragment.add_content(loader.render_template(self.STAGE_WRAPPER_TEMPLATE, render_context))
        if stage_fragment.js_init_fn:
            fragment.initialize_js(stage_fragment.js_init_fn)

        return fragment

    @outsider_disallowed_protected_view
    def student_view(self, context):
        return self._view_render(context)

    @outsider_disallowed_protected_view
    def author_preview_view(self, context):
        # if we use student_view or author_view Studio will wrap it in HTML that we don't want in the preview
        fragment = self._view_render(context, "preview_view")
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_frag_resources(url_name_fragment)
        return fragment

    @outsider_disallowed_protected_view
    def author_edit_view(self, context):
        fragment = super(BaseGroupActivityStage, self).author_edit_view(context)
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_frag_resources(url_name_fragment)
        return fragment

    def render_children_fragments(self, context, view='student_view'):
        children_fragments = []
        for child in self._children:
            child_fragment = self._render_child_fragment(child, context, view)
            children_fragments.append(child_fragment)

        return children_fragments

    def get_stage_content_fragment(self, context, view='student_view'):
        fragment = Fragment()
        children_fragments = self.render_children_fragments(context, view=view)
        render_context = {
            'stage': self,
            'children_contents': [frag.content for frag in children_fragments]
        }

        for frag in children_fragments:
            fragment.add_frag_resources(frag)

        render_context.update(context)
        fragment.add_content(loader.render_template(self.STAGE_CONTENT_TEMPLATE, render_context))

        if self.js_file:
            fragment.add_javascript_url(self.runtime.local_resource_url(self, self.js_file))

        if self.js_init:
            fragment.initialize_js(self.js_init)

        return fragment

    def mark_complete(self, user_id=None):
        user_id = user_id if user_id is not None else self.user_id
        try:
            self.project_api.mark_as_complete(self.course_id, self.content_id, user_id, self.id)
        except ApiError as exc:
            # 409 indicates that the completion record already existed # That's ok in this case
            if exc.code != 409:
                raise

    def get_stage_state(self):
        """
        Gets stage completion state
        """
        completed_users = self.project_api.get_stage_state(self.course_id, self.activity.id, self.id)

        if self.user_id in completed_users:
            return StageState.COMPLETED
        else:
            return StageState.NOT_STARTED

    def navigation_view(self, context):
        fragment = Fragment()
        rendering_context = {
            'stage': self,
            'activity_id': self.activity.id,
            'stage_state': self.get_stage_state(),
            'block_link': get_link_to_block(self),
            'is_current_stage': self.is_current_stage(context)
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

    def get_new_stage_state_data(self):
        return {
            "activity_id": str(self.activity.id),
            "stage_id": str(self.id),
            "state": self.get_stage_state()
        }


class BasicStage(BaseGroupActivityStage):
    CATEGORY = 'gp-v2-stage-basic'

    NAVIGATION_LABEL = _(u'Overview')
    STUDIO_LABEL = _(u"Overview")

    def student_view(self, context):
        fragment = super(BasicStage, self).student_view(context)

        if self.available_now and not self.is_admin_grader:
            self.mark_complete()

        return fragment


class CompletionStage(BaseGroupActivityStage):
    completed = Boolean(
        display_name=_(u"Completed"),
        scope=Scope.user_state
    )

    CATEGORY = 'gp-v2-stage-completion'
    STAGE_CONTENT_TEMPLATE = "templates/html/stages/completion.html"

    NAVIGATION_LABEL = _(u'Task')
    STUDIO_LABEL = _(u"Completion")

    js_file = "public/js/stages/completion.js"
    js_init = "GroupProjectCompletionStage"

    STAGE_ACTION = _(u"mark stage as complete")

    @XBlock.json_handler
    @outsider_disallowed_protected_handler
    def stage_completed(self, data, suffix=''):  # pylint: disable=unused-argument
        if not self.available_now:
            template = self.STAGE_NOT_OPEN_MESSAGE if not self.is_open else self.STAGE_CLOSED_MESSAGE
            return {'result': 'error',  'msg': template.format(action=self.STAGE_ACTION)}

        try:
            self.mark_complete()
            self.completed = True
            return {
                'result': 'success',
                'msg': _('Stage completed!'),
                'new_stage_states': [self.get_new_stage_state_data()]
            }
        except ApiError as exception:
            log.exception(exception.message)
            return {'result': 'error', 'msg': exception.message}

    def get_stage_content_fragment(self, context, view='student_view'):
        extra_context = {
            'completed': self.completed
        }
        extra_context.update(context)
        return super(CompletionStage, self).get_stage_content_fragment(extra_context, view)


class SubmissionStage(BaseGroupActivityStage):
    CATEGORY = 'gp-v2-stage-submission'

    NAVIGATION_LABEL = _(u'Task')
    STUDIO_LABEL = _(u"Deliverable")

    submissions_stage = True

    STAGE_ACTION = _(u"upload submission")

    @property
    def allowed_nested_blocks(self):
        blocks = super(SubmissionStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (GroupProjectSubmissionXBlock.CATEGORY, GroupProjectSubmissionXBlock.STUDIO_LABEL),
            (SubmissionsStaticContentXBlock.CATEGORY, SubmissionsStaticContentXBlock.STUDIO_LABEL)
        ]))
        return blocks

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
    def has_some_submissions(self):
        return any(submission.upload is not None for submission in self.submissions)

    @property
    def has_all_submissions(self):
        return all(submission.upload is not None for submission in self.submissions)

    def check_submissions_and_mark_complete(self):
        if self.has_all_submissions:
            for user in self.workgroup["users"]:
                self.mark_complete(user["id"])

    def get_stage_state(self):
        if self.has_all_submissions:
            return StageState.COMPLETED
        elif self.has_some_submissions:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def _render_view(self, child_view, template, context):
        fragment = Fragment()

        submission_contents = []
        for submission in self.submissions:
            submission_fragment = submission.render(child_view, context)
            fragment.add_frag_resources(submission_fragment)
            submission_contents.append(submission_fragment.content)

        context = {'stage': self, 'submission_contents': submission_contents}
        fragment.add_content(loader.render_template(template, context))

        return fragment

    def submissions_view(self, context):
        return self._render_view('submissions_view', "templates/html/stages/submissions_view.html", context)

    def review_submissions_view(self, context):
        # transparently passing group_id via context
        return self._render_view(
            'submission_review_view', "templates/html/stages/submissions_review_view.html", context
        )


class ReviewBaseStage(BaseGroupActivityStage):
    NAVIGATION_LABEL = _(u'Task')

    js_file = "public/js/stages/review_stage.js"
    js_init = "GroupProjectReviewStage"

    STAGE_ACTION = _(u"save feedback")

    TA_GRADING_NOT_ALLOWED = _(u"TA grading is not allowed for this stage")

    @property
    def allowed_nested_blocks(self):
        blocks = super(ReviewBaseStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (GroupProjectReviewQuestionXBlock.CATEGORY, GroupProjectReviewQuestionXBlock.STUDIO_LABEL),
            (GradeRubricStaticContentXBlock.CATEGORY, GradeRubricStaticContentXBlock.STUDIO_LABEL)
        ]))
        return blocks

    @property
    def questions(self):
        return self._get_children_by_category(GroupProjectReviewQuestionXBlock.CATEGORY)

    @property
    def required_questions(self):
        return [question for question in self.questions if question.required]

    @property
    def grade_questions(self):
        return [question for question in self.questions if question.grade]

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

    def _check_review_status(self, items_to_grade, review_items, review_item_key):
        my_feedback = {
            make_key(peer_review_item[review_item_key], peer_review_item["question"]): peer_review_item["answer"]
            for peer_review_item in review_items
            if peer_review_item['reviewer'] == self.anonymous_student_id
        }

        required_keys = [
            make_key(item["id"], question.question_id)
            for item in items_to_grade
            for question in self.required_questions
        ]
        has_all = True
        has_some = False

        for key in required_keys:
            has_answer = my_feedback.get(key, None) not in (None, '')
            has_all = has_all and has_answer
            has_some = has_some or has_answer

        if has_all:
            return ReviewState.COMPLETED
        elif has_some:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def get_stage_state(self):
        review_status = self.review_status()
        if review_status == ReviewState.COMPLETED:
            return StageState.COMPLETED
        elif review_status == ReviewState.INCOMPLETE:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def _pivot_feedback(self, feedback):  # pylint: disable=no-self-use
        """
        Pivots the feedback to show question -> answer
        """
        return {pi['question']: pi['answer'] for pi in feedback}

    @XBlock.json_handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    def submit_review(self, submissions, context=''):  # pylint: disable=unused-argument
        # if admin grader - still allow providing grades even for non-TA-graded activities
        if self.is_admin_grader and not self.allow_admin_grader_access:
            return {'result': 'error', 'msg': self.TA_GRADING_NOT_ALLOWED}

        if not self.available_now:
            reason = self.STAGE_NOT_OPEN_TEMPLATE if not self.is_open else self.STAGE_CLOSED_TEMPLATE
            return {'result': 'error', 'msg': reason.format(action=self.STAGE_ACTION)}

        try:
            self.do_submit_review(submissions)

            if self.is_group_member and self.review_status() == ReviewState.COMPLETED:
                self.mark_complete()
        except ApiError as exception:
            log.exception(exception.message)
            return {'result': 'error', 'msg': exception.message}

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
            'new_stage_states': [self.get_new_stage_state_data()]
        }

    def do_submit_review(self, submissions):
        pass


class TeamEvaluationStage(ReviewBaseStage):
    CATEGORY = 'gp-v2-stage-team-evaluation'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/team_evaluation.html'

    STUDIO_LABEL = _(u"Team Evaluation")

    @property
    def allowed_nested_blocks(self):
        blocks = super(TeamEvaluationStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (PeerSelectorXBlock.CATEGORY, PeerSelectorXBlock.STUDIO_LABEL)
        ]))
        return blocks

    @property
    def team_members(self):
        """
        Returns teammates to review. May throw `class`: OutsiderDisallowedError
        """
        if not self.is_group_member:
            return []

        try:
            return [
                self.project_api.get_user_details(team_member["id"])
                for team_member in self.workgroup["users"]
                if self.user_id != int(team_member["id"])
            ]
        except ApiError:
            return []

    def review_status(self):
        peers_to_review = [user for user in self.workgroup["users"] if user["id"] != self.user_id]
        peer_review_items = self.project_api.get_peer_review_items_for_group(self.workgroup['id'], self.content_id)

        return self._check_review_status(peers_to_review, peer_review_items, "user")

    def validate(self):
        violations = super(TeamEvaluationStage, self).validate()

        # Technically, nothing prevents us from allowing graded peer review questions. The only reason why
        # they are considered not supported is that GroupActivityXBlock.calculate_grade does not
        # take them into account.
        if self.grade_questions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Grade questions are not supported for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    def load_peer_feedback(self, request, suffix=''):  # pylint: disable=unused-argument
        feedback = self.project_api.get_peer_review_items(
            self.anonymous_student_id,
            request.GET["peer_id"],
            self.workgroup['id'],
            self.content_id,
        )
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        peer_id = submissions["review_subject_id"]
        del submissions["review_subject_id"]

        self.project_api.submit_peer_review_items(
            self.anonymous_student_id,
            peer_id,
            self.workgroup['id'],
            self.content_id,
            submissions,
        )


class PeerReviewStage(ReviewBaseStage):
    CATEGORY = 'gp-v2-stage-peer-review'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_review.html'

    STUDIO_LABEL = _(u"Peer Grading")

    @property
    def allowed_nested_blocks(self):
        blocks = super(PeerReviewStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (GroupSelectorXBlock.CATEGORY, GroupSelectorXBlock.STUDIO_LABEL)
        ]))
        return blocks

    @property
    def allow_admin_grader_access(self):
        return True

    @property
    def review_groups(self):
        """
        Returns groups to review. May throw `class`: OutsiderDisallowedError
        """
        if not self.is_group_member:
            return [self.workgroup]

        try:
            return self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        except ApiError:
            return []

    def review_status(self):
        groups_to_review = self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)

        group_review_items = []
        for assess_group in groups_to_review:
            group_review_items.extend(
                self.project_api.get_workgroup_review_items_for_group(assess_group["id"], self.content_id)
            )

        return self._check_review_status(groups_to_review, group_review_items, "workgroup")

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    def other_submission_links(self, request, suffix=''):  # pylint: disable=unused-argument
        group_id = request.GET["group_id"]

        target_stages = [stage for stage in self.activity.stages if stage.submissions_stage]

        submission_stage_contents = []
        for stage in target_stages:
            stage_fragment = stage.render('review_submissions_view', {'group_id': group_id})
            submission_stage_contents.append(stage_fragment.content)

        context = {'block': self, 'submission_stage_contents': submission_stage_contents}
        html_output = loader.render_template(
            '/templates/html/stages/stages_group_review_other_team_submissions.html', context
        )

        return webob.response.Response(body=json.dumps({"html": html_output}))

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    def load_other_group_feedback(self, request, suffix=''):  # pylint: disable=unused-argument
        group_id = request.GET["group_id"]
        feedback = self.project_api.get_workgroup_review_items(self.anonymous_student_id, group_id, self.content_id)
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        group_id = submissions["review_subject_id"]
        del submissions["review_subject_id"]

        self.project_api.submit_workgroup_review_items(
            self.anonymous_student_id,
            group_id,
            self.content_id,
            submissions
        )

        for question_id in self.grade_questions:
            if question_id in submissions:
                # Emit analytics event...
                self.runtime.publish(
                    self,
                    "group_activity.received_grade_question_score",
                    {
                        "question": question_id,
                        "answer": submissions[question_id],
                        "reviewer_id": self.anonymous_student_id,
                        "is_admin_grader": self.is_admin_grader,
                        "group_id": group_id,
                        "content_id": self.content_id,
                    }
                )

        self.activity.calculate_and_send_grade(group_id)


class FeedbackDisplayBaseStage(BaseGroupActivityStage):
    NAVIGATION_LABEL = _(u'Review')

    def validate(self):
        violations = super(FeedbackDisplayBaseStage, self).validate()

        if not self.assessments:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Assessments are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations

    def student_view(self, context):
        fragment = super(FeedbackDisplayBaseStage, self).student_view(context)

        # TODO: should probably check for all reviews to be ready
        if self.available_now and not self.is_admin_grader:
            self.mark_complete()

        return fragment


class EvaluationDisplayStage(FeedbackDisplayBaseStage):
    CATEGORY = 'gp-v2-stage-evaluation-display'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/evaluation_display.html'

    STUDIO_LABEL = _(u"Evaluation Display")

    type = u'Evaluation'

    def allowed_nested_blocks(self):
        blocks = super(FeedbackDisplayBaseStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (GroupProjectTeamEvaluationDisplayXBlock.CATEGORY, GroupProjectTeamEvaluationDisplayXBlock.STUDIO_LABEL)
        ]))
        return blocks

    @property
    def assessments(self):
        return self._get_children_by_category(GroupProjectTeamEvaluationDisplayXBlock.CATEGORY)


class GradeDisplayStage(FeedbackDisplayBaseStage):
    CATEGORY = 'gp-v2-stage-grade-display'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/grade_display.html'

    STUDIO_LABEL = _(u"Grade Display")

    def allowed_nested_blocks(self):
        blocks = super(FeedbackDisplayBaseStage, self).allowed_nested_blocks
        blocks.update(OrderedDict([
            (GroupProjectGradeEvaluationDisplayXBlock.CATEGORY, GroupProjectGradeEvaluationDisplayXBlock.STUDIO_LABEL)
        ]))
        return blocks

    @property
    def assessments(self):
        return self._get_children_by_category(GroupProjectGradeEvaluationDisplayXBlock.CATEGORY)

    def get_stage_content_fragment(self, context, view='student_view'):
        final_grade = self.activity.calculate_grade(self.workgroup['id'])
        context_extension = {
            'final_grade': final_grade if final_grade is not None else _(u"N/A")
        }
        context_extension.update(context)
        return super(GradeDisplayStage, self).get_stage_content_fragment(context_extension, view)


STAGE_TYPES = (
    BasicStage.CATEGORY,
    CompletionStage.CATEGORY,
    SubmissionStage.CATEGORY,
    TeamEvaluationStage.CATEGORY,
    PeerReviewStage.CATEGORY,
    EvaluationDisplayStage.CATEGORY,
    GradeDisplayStage.CATEGORY
)

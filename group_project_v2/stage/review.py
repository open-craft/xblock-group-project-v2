import json
import logging
import webob
from xblock.core import XBlock
from xblock.fields import String, Scope, Boolean
from xblock.validation import ValidationMessage
from group_project_v2.api_error import ApiError
from group_project_v2.stage.base import BaseGroupActivityStage
from group_project_v2.stage_components import (
    GradeRubricStaticContentXBlock, GroupProjectReviewQuestionXBlock, PeerSelectorXBlock, GroupSelectorXBlock
)
from group_project_v2.utils import (
    loader, gettext as _, make_key,
    outsider_disallowed_protected_handler, key_error_protected_handler, conversion_protected_handler,
    MUST_BE_OVERRIDDEN)
from group_project_v2.stage.utils import StageState, ReviewState, DISPLAY_NAME_NAME, DISPLAY_NAME_HELP

log = logging.getLogger(__name__)


class ReviewBaseStage(BaseGroupActivityStage):
    NAVIGATION_LABEL = _(u'Task')

    visited = Boolean(default=False, scope=Scope.user_state)

    js_file = "public/js/stages/review_stage.js"
    js_init = "GroupProjectReviewStage"

    STAGE_ACTION = _(u"save feedback")
    FEEDBACK_SAVED_MESSAGE = _(u'Thanks for your feedback.')

    TA_GRADING_NOT_ALLOWED = _(u"TA grading is not allowed for this stage")

    @property
    def allowed_nested_blocks(self):
        blocks = super(ReviewBaseStage, self).allowed_nested_blocks
        blocks.extend([GradeRubricStaticContentXBlock, GroupProjectReviewQuestionXBlock])
        return blocks

    @property
    def questions(self):
        return self.get_children_by_category(GroupProjectReviewQuestionXBlock.CATEGORY)

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

        if not self.visited:
            return StageState.NOT_STARTED

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
    @conversion_protected_handler
    def submit_review(self, submissions, context=''):  # pylint: disable=unused-argument
        # if admin grader - still allow providing grades even for non-TA-graded activities
        if self.is_admin_grader and not self.allow_admin_grader_access:
            return {'result': 'error', 'msg': self.TA_GRADING_NOT_ALLOWED}

        if not self.available_now:
            reason = self.STAGE_NOT_OPEN_TEMPLATE if not self.is_open else self.STAGE_CLOSED_TEMPLATE
            return {'result': 'error', 'msg': reason.format(action=self.STAGE_ACTION)}

        try:
            self.do_submit_review(submissions)

            if self.can_mark_complete and self.review_status() == ReviewState.COMPLETED:
                self.mark_complete()
        except ApiError as exception:
            log.exception(exception.message)
            return {'result': 'error', 'msg': exception.message}

        return {
            'result': 'success',
            'msg': self.FEEDBACK_SAVED_MESSAGE,
            'new_stage_states': [self.get_new_stage_state_data()]
        }

    def do_submit_review(self, submissions):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def student_view(self, context):
        if self.can_mark_complete:
            self.visited = True

        return super(ReviewBaseStage, self).student_view(context)


class TeamEvaluationStage(ReviewBaseStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Team Evaluation Stage")
    )

    CATEGORY = 'gp-v2-stage-team-evaluation'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/team_evaluation.html'

    STUDIO_LABEL = _(u"Team Evaluation")

    @property
    def allowed_nested_blocks(self):
        blocks = super(TeamEvaluationStage, self).allowed_nested_blocks
        blocks.extend([PeerSelectorXBlock])
        return blocks

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
                _(u"Grade questions are not supported for {class_name} stage '{stage_title}'").format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name
                )
            ))

        if not self.has_child_of_category(PeerSelectorXBlock.CATEGORY):
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(
                    u"{class_name} stage '{stage_title}' is missing required component '{peer_selector_class_name}'"
                ).format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name,
                    peer_selector_class_name=PeerSelectorXBlock.STUDIO_LABEL
                )
            ))

        return violations

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    @conversion_protected_handler
    def load_peer_feedback(self, request, suffix=''):  # pylint: disable=unused-argument
        peer_id = int(request.GET["peer_id"])
        feedback = self.project_api.get_peer_review_items(
            self.anonymous_student_id,
            peer_id,
            self.workgroup['id'],
            self.content_id,
        )
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        peer_id = int(submissions["review_subject_id"])
        del submissions["review_subject_id"]

        self.project_api.submit_peer_review_items(
            self.anonymous_student_id,
            peer_id,
            self.workgroup['id'],
            self.content_id,
            submissions,
        )


class PeerReviewStage(ReviewBaseStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Peer Grading Stage")
    )

    CATEGORY = 'gp-v2-stage-peer-review'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_review.html'

    STUDIO_LABEL = _(u"Peer Grading")

    @property
    def allowed_nested_blocks(self):
        blocks = super(PeerReviewStage, self).allowed_nested_blocks
        blocks.extend([GroupSelectorXBlock])
        return blocks

    @property
    def allow_admin_grader_access(self):
        return True

    @property
    def review_groups(self):
        """
        Returns groups to review. May throw `class`: OutsiderDisallowedError
        """
        if self.is_admin_grader:
            return [self.workgroup]

        try:
            return self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        except ApiError:
            return []

    @property
    def available_to_current_user(self):
        if not super(PeerReviewStage, self).available_to_current_user:
            return False

        if not self.is_admin_grader and self.activity.is_ta_graded:
            return False

        return True

    @property
    def is_graded_stage(self):
        return True

    def review_status(self):
        if not self.is_admin_grader:
            groups_to_review = self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        else:
            groups_to_review = [self.workgroup]

        group_review_items = []
        for assess_group in groups_to_review:
            group_review_items.extend(
                self.project_api.get_workgroup_review_items_for_group(assess_group["id"], self.content_id)
            )

        return self._check_review_status(groups_to_review, group_review_items, "workgroup")

    def validate(self):
        violations = super(PeerReviewStage, self).validate()

        if not self.grade_questions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Grade questions are required for {class_name} stage '{stage_title}'").format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name
                )
            ))

        if not self.has_child_of_category(GroupSelectorXBlock.CATEGORY):
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(
                    u"{class_name} stage '{stage_title}' is missing required component '{group_selector_class_name}'"
                ).format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name,
                    group_selector_class_name=GroupSelectorXBlock.STUDIO_LABEL
                )
            ))

        return violations

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    @conversion_protected_handler
    def other_submission_links(self, request, suffix=''):  # pylint: disable=unused-argument
        group_id = int(request.GET["group_id"])

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
        group_id = int(request.GET["group_id"])
        feedback = self.project_api.get_workgroup_review_items(self.anonymous_student_id, group_id, self.content_id)
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        group_id = int(submissions["review_subject_id"])
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

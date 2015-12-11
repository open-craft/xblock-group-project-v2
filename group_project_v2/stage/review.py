import json
import logging

import itertools
from collections import defaultdict

from lazy.lazy import lazy
import webob
from xblock.core import XBlock
from xblock.fields import String, Scope, Boolean
from xblock.validation import ValidationMessage

from group_project_v2 import messages
from group_project_v2.api_error import ApiError
from group_project_v2.stage.base import BaseGroupActivityStage
from group_project_v2.stage_components import (
    GradeRubricStaticContentXBlock, GroupProjectReviewQuestionXBlock, PeerSelectorXBlock, GroupSelectorXBlock
)
from group_project_v2.utils import (
    loader, gettext as _, make_key,
    outsider_disallowed_protected_handler, key_error_protected_handler, conversion_protected_handler,
    MUST_BE_OVERRIDDEN, memoize_with_expiration
)
from group_project_v2.stage.utils import StageState, ReviewState, DISPLAY_NAME_NAME, DISPLAY_NAME_HELP

log = logging.getLogger(__name__)


class ReviewBaseStage(BaseGroupActivityStage):
    NAVIGATION_LABEL = _(u'Task')

    visited = Boolean(default=False, scope=Scope.user_state)

    js_file = "public/js/stages/review_stage.js"
    js_init = "GroupProjectReviewStage"

    REVIEW_ITEM_KEY = None

    STAGE_ACTION = _(u"save feedback")

    # (has_some, has_all) -> ReviewState. have_all = True and have_some = False is obviously an error
    REVIEW_STATE_CONDITIONS = {
        (True, True): ReviewState.COMPLETED,
        (True, False): ReviewState.INCOMPLETE,
        (False, False): ReviewState.NOT_STARTED
    }

    # pretty much obvious mapping, but still it is useful to separate the two - more stage states could be theoretically
    # added, i.e. Open, Closed, etc. THose won't have a mapping to ReviewState
    STAGE_STATE_REVIEW_STATE_MAPPING = {
        ReviewState.COMPLETED: StageState.COMPLETED,
        ReviewState.INCOMPLETE: StageState.INCOMPLETE,
        ReviewState.NOT_STARTED: StageState.NOT_STARTED,
    }

    @property
    def allowed_nested_blocks(self):
        blocks = super(ReviewBaseStage, self).allowed_nested_blocks
        blocks.extend([GradeRubricStaticContentXBlock, GroupProjectReviewQuestionXBlock])
        return blocks

    @property
    def review_subjects(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

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
                messages.QUESTION_BLOCKS_ARE_MISSING.format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations

    def _convert_review_items_to_keys(self, review_items):
        empty_values = (None, '')
        return set(
            make_key(review_item[self.REVIEW_ITEM_KEY], review_item["question"])
            for review_item in review_items
            if review_item["answer"] not in empty_values
        )

    def _make_required_keys(self, items_to_grade):
        return set(
            make_key(item_id, question.question_id)
            for item_id in items_to_grade
            for question in self.required_questions
        )

    def _calculate_review_status(self, items_to_grade, reviewer_feedback_keys):
        """
        Calculates review status for all reviewers listed in review_items collection
        :param collections.Iterable[int] items_to_grade: Ids of review subjects (teammates or other groups)
        :param collections.Iterable[set[str]] reviewer_feedback_keys: Review feedback keys
        :rtype: ReviewState
        """
        required_keys = self._make_required_keys(items_to_grade)
        has_all = bool(required_keys) and reviewer_feedback_keys >= required_keys
        has_some = bool(reviewer_feedback_keys & required_keys)

        return self.REVIEW_STATE_CONDITIONS.get((has_some, has_all))

    def _check_review_status(self, items_to_grade, review_items):
        """
        Calculates review status for current user
        :param collections.Iterable[int] items_to_grade: Ids of review subjects (teammates or other groups)
        :param collections.Iterable[dict] review_items: review items (answers to review questions)
        :rtype: ReviewState
        """
        my_feedback = [item for item in review_items if item['reviewer'] == self.anonymous_student_id]
        my_review_keys = self._convert_review_items_to_keys(my_feedback)
        return self._calculate_review_status(items_to_grade, my_review_keys)

    def get_stage_state(self):
        review_status = self.review_status()

        if not self.visited:
            return StageState.NOT_STARTED

        return self.STAGE_STATE_REVIEW_STATE_MAPPING[review_status]

    def _pivot_feedback(self, feedback):  # pylint: disable=no-self-use
        """
        Pivots the feedback to show question -> answer
        """
        return {pi['question']: pi['answer'] for pi in feedback}

    def get_users_completion(self, target_workgroups, target_users):
        """
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_users:
        :rtype: (set[int], set[int])
        """
        completed_users, partially_completed_users = set(), set()

        for user in target_users:
            review_items, review_subjects = self.get_review_data(user.id)
            review_keys = self._convert_review_items_to_keys(review_items)
            review_status = self._calculate_review_status(review_subjects, review_keys)

            if review_status == ReviewState.COMPLETED:
                completed_users.add(user.id)
            elif review_status == ReviewState.INCOMPLETE:
                partially_completed_users.add(user.id)

        return completed_users, partially_completed_users

    def get_review_data(self, user_id):
        """
        :param gint user_id:
        :rtype: (dict, set[int])
        """
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    @XBlock.json_handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    @conversion_protected_handler
    def submit_review(self, submissions, _context=''):
        # if admin grader - still allow providing grades even for non-TA-graded activities
        if self.is_admin_grader and not self.allow_admin_grader_access:
            return {'result': 'error', 'msg': messages.TA_GRADING_NOT_ALLOWED}

        if not self.available_now:
            reason = messages.STAGE_NOT_OPEN_TEMPLATE if not self.is_open else messages.STAGE_CLOSED_TEMPLATE
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
            'msg': messages.FEEDBACK_SAVED_MESSAGE,
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

    REVIEW_ITEM_KEY = "user"

    @lazy
    def review_subjects(self):
        return [user for user in self.workgroup.users if user.id != self.user_id]

    @property
    def allowed_nested_blocks(self):
        blocks = super(TeamEvaluationStage, self).allowed_nested_blocks
        blocks.extend([PeerSelectorXBlock])
        return blocks

    def review_status(self):
        peer_review_items = self.project_api.get_peer_review_items_for_group(
            self.workgroup.id, self.activity_content_id
        )

        return self._check_review_status([user.id for user in self.review_subjects], peer_review_items)

    def get_review_data(self, user_id):
        """
        :param int user_id: User ID
        :rtype: (dict, set[int])
        """
        workgroup = self.project_api.get_user_workgroup_for_course(user_id, self.course_id)
        review_subjects = set(user.id for user in workgroup.users) - {user_id}
        review_items = [
            item
            for item in self._get_review_items_for_group(self.project_api, workgroup.id, self.activity_content_id)
            if self.real_user_id(item['reviewer']) == user_id
        ]
        return review_items, review_subjects

    @staticmethod
    @memoize_with_expiration()
    def _get_review_items_for_group(project_api, workgroup_id, activity_content_id):
        return project_api.get_peer_review_items_for_group(workgroup_id, activity_content_id)

    def validate(self):
        violations = super(TeamEvaluationStage, self).validate()

        # Technically, nothing prevents us from allowing graded peer review questions. The only reason why
        # they are considered not supported is that GroupActivityXBlock.calculate_grade does not
        # take them into account.
        if self.grade_questions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                messages.GRADED_QUESTIONS_NOT_SUPPORTED.format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name
                )
            ))

        if not self.has_child_of_category(PeerSelectorXBlock.CATEGORY):
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                messages.PEER_SELECTOR_BLOCK_IS_MISSING.format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name,
                    peer_selector_class_name=PeerSelectorXBlock.STUDIO_LABEL
                )
            ))

        return violations

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    @conversion_protected_handler
    def load_peer_feedback(self, request, _suffix=''):
        peer_id = int(request.GET["peer_id"])
        feedback = self.project_api.get_peer_review_items(
            self.anonymous_student_id,
            peer_id,
            self.workgroup.id,
            self.activity_content_id,
        )
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        peer_id = int(submissions["review_subject_id"])
        del submissions["review_subject_id"]

        self.project_api.submit_peer_review_items(
            self.anonymous_student_id,
            peer_id,
            self.workgroup.id,
            self.activity_content_id,
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

    REVIEW_ITEM_KEY = "workgroup"

    @property
    def allowed_nested_blocks(self):
        blocks = super(PeerReviewStage, self).allowed_nested_blocks
        blocks.extend([GroupSelectorXBlock])
        return blocks

    @property
    def allow_admin_grader_access(self):
        return True

    @lazy
    def review_subjects(self):
        """
        Returns groups to review. May throw `class`: OutsiderDisallowedError
        :rtype: list[group_project_v2.project_api.dtos.WorkgroupDetails]
        """
        if self.is_admin_grader:
            return [self.workgroup]

        try:
            return self.get_review_subjects(self.user_id)
        except ApiError:
            log.exception("Error obtaining list of groups to grade - assuming no groups to grade")
            return []

    @property
    def review_groups(self):
        return self.review_subjects

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

    @property
    def can_mark_complete(self):
        if self.is_admin_grader:
            return True
        return super(PeerReviewStage, self).can_mark_complete

    def _get_review_items(self, review_groups, with_caching=False):
        """
        Gets review items for a list of groups
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] review_groups: Target groups
        :param bool with_caching:
            Underlying implementation uses get_workgroup_review_items_for_group for both cached and non-cached version.
            However, one of the users of this method (get_review_data) might benefit from caching,
            while the other (review_status) is affected by the issue outlined in get_workgroup_review_items_for_group
            comment (i.e. cached value is not updated when new feedback is posted).
            So, caching is conditionally enabled here to serve both users of this method as efficiently as possible.
        :return:
        """
        def do_get_items(group_id):
            if with_caching:
                return self._get_review_items_for_group(self.project_api, group_id, self.activity_content_id)
            else:
                return self.project_api.get_workgroup_review_items_for_group(group_id, self.activity_content_id)

        return list(itertools.chain.from_iterable(do_get_items(group.id) for group in review_groups))

    def review_status(self):
        group_review_items = self._get_review_items(self.review_groups, with_caching=False)
        return self._check_review_status([group.id for group in self.review_groups], group_review_items)

    def _calculate_group_review_status(self, ta_review_keys, target_workgroups):
        group_statuses = {}
        for group in target_workgroups:
            for reviewer, reviewer_keys in ta_review_keys.iteritems():
                group_review_status = self._calculate_review_status([group.id], reviewer_keys)
                if group_review_status == ReviewState.COMPLETED:
                    group_statuses[group.id] = ReviewState.COMPLETED
                    break
                if group_review_status == ReviewState.INCOMPLETE:
                    group_statuses[group.id] = ReviewState.INCOMPLETE  # but no break - could be improved by other TA
        return group_statuses

    def _get_ta_review_keys(self, target_workgroups):
        review_items = self._get_review_items(target_workgroups, with_caching=False)

        grouped_items = defaultdict(list)
        for item in review_items:
            grouped_items[item['reviewer']].append(item)

        ta_review_keys = {
            reviewer: self._convert_review_items_to_keys(review_items)
            for reviewer, items in grouped_items.iteritems()
            if self._confirm_outsider_allowed(self.project_api, self.real_user_id(reviewer), self.course_id)
        }
        return ta_review_keys

    def get_users_completion(self, target_workgroups, target_users):
        if not self.activity.is_ta_graded:
            return super(PeerReviewStage, self).get_users_completion(target_workgroups, target_users)

        ta_review_keys = self._get_ta_review_keys(target_workgroups)
        group_statuses = self._calculate_group_review_status(ta_review_keys, target_workgroups)

        completed_users, partially_completed_users = set(), set()
        for group in target_workgroups:
            if group.id not in group_statuses:
                continue

            group_users = set(user.id for user in group.users)

            if group_statuses[group.id] == ReviewState.COMPLETED:
                completed_users |= group_users
            if group_statuses[group.id] == ReviewState.INCOMPLETE:
                partially_completed_users |= group_users

        return completed_users, partially_completed_users

    def get_review_data(self, user_id):
        """
        :param int user_id:
        :rtype: (dict, set[int])
        """
        review_subjects = self.get_review_subjects(user_id)
        review_items = [
            item
            for item in self._get_review_items(review_subjects, with_caching=True)
            if self.real_user_id(item['reviewer']) == user_id
        ]
        return review_items, set(group.id for group in review_subjects)

    def get_review_subjects(self, user_id):
        """
        Gets
        :param int user_id: User ID
        :return:
        """
        return self.project_api.get_workgroups_to_review(user_id, self.course_id, self.activity_content_id)

    @staticmethod
    @memoize_with_expiration()
    def _get_review_items_for_group(project_api, workgroup_id, activity_content_id):
        return project_api.get_workgroup_review_items_for_group(workgroup_id, activity_content_id)

    def validate(self):
        violations = super(PeerReviewStage, self).validate()

        if not self.grade_questions:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                messages.GRADED_QUESTIONS_ARE_REQUIRED.format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name
                )
            ))

        if not self.has_child_of_category(GroupSelectorXBlock.CATEGORY):
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                messages.GROUP_SELECTOR_BLOCK_IS_MISSING.format(
                    class_name=self.STUDIO_LABEL, stage_title=self.display_name,
                    group_selector_class_name=GroupSelectorXBlock.STUDIO_LABEL
                )
            ))

        return violations

    def get_stage_state(self):
        if not self.review_subjects:
            return StageState.NOT_STARTED

        return super(PeerReviewStage, self).get_stage_state()

    @XBlock.handler
    @outsider_disallowed_protected_handler
    @key_error_protected_handler
    @conversion_protected_handler
    def other_submission_links(self, request, _suffix=''):
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
    def load_other_group_feedback(self, request, _suffix=''):
        group_id = int(request.GET["group_id"])
        feedback = self.project_api.get_workgroup_review_items(
            self.anonymous_student_id, group_id, self.activity_content_id
        )
        results = self._pivot_feedback(feedback)

        return webob.response.Response(body=json.dumps(results))

    def do_submit_review(self, submissions):
        group_id = int(submissions["review_subject_id"])
        del submissions["review_subject_id"]

        self.project_api.submit_workgroup_review_items(
            self.anonymous_student_id,
            group_id,
            self.activity_content_id,
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
                        "content_id": self.activity_content_id,
                    }
                )

        self.activity.calculate_and_send_grade(group_id)

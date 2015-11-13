import itertools
import logging
from lazy.lazy import lazy
from xblock.fields import String, Scope
from xblock.validation import ValidationMessage
from group_project_v2.stage.utils import DISPLAY_NAME_NAME, DISPLAY_NAME_HELP
from group_project_v2.stage.base import BaseGroupActivityStage
from group_project_v2.stage.mixins import SimpleCompletionStageMixin
from group_project_v2.stage_components import (
    GroupProjectTeamEvaluationDisplayXBlock, GroupProjectGradeEvaluationDisplayXBlock
)
from group_project_v2.utils import gettext as _, MUST_BE_OVERRIDDEN


log = logging.getLogger(__name__)


class FeedbackDisplayBaseStage(SimpleCompletionStageMixin, BaseGroupActivityStage):
    NAVIGATION_LABEL = _(u'Review')
    FEEDBACK_DISPLAY_BLOCK_CATEGORY = None

    @property
    def feedback_display_blocks(self):
        return self.get_children_by_category(self.FEEDBACK_DISPLAY_BLOCK_CATEGORY)

    @lazy
    def required_questions(self):
        return [
            feedback_display.question_id for feedback_display in self.feedback_display_blocks
            if feedback_display.question and feedback_display.question.required
        ]

    def get_reviewer_ids(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def get_reviews(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def _make_review_keys(self, review_items):
        return [(self.real_user_id(item['reviewer']), item['question']) for item in review_items]

    def validate(self):
        violations = super(FeedbackDisplayBaseStage, self).validate()

        if not self.feedback_display_blocks:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Feedback display blocks are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations

    def student_view(self, context):
        fragment = super(FeedbackDisplayBaseStage, self).student_view(context)

        # TODO: should probably check for all reviews to be ready
        if self.can_mark_complete:
            self.mark_complete()

        return fragment


class EvaluationDisplayStage(FeedbackDisplayBaseStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Evaluation Display Stage")
    )

    CATEGORY = 'gp-v2-stage-evaluation-display'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/evaluation_display.html'

    STUDIO_LABEL = _(u"Evaluation Display")
    FEEDBACK_DISPLAY_BLOCK_CATEGORY = GroupProjectTeamEvaluationDisplayXBlock.CATEGORY

    type = u'Evaluation'

    @property
    def can_mark_complete(self):
        base_result = super(EvaluationDisplayStage, self).can_mark_complete
        if not base_result:
            return False

        reviewer_ids = self.get_reviewer_ids()

        required_reviews = set(itertools.product(reviewer_ids, self.required_questions))
        performed_reviews = set(self._make_review_keys(self.get_reviews()))

        return performed_reviews >= required_reviews

    @property
    def allowed_nested_blocks(self):
        blocks = super(EvaluationDisplayStage, self).allowed_nested_blocks
        blocks.extend([GroupProjectTeamEvaluationDisplayXBlock])
        return blocks

    def get_reviewer_ids(self):
        return [user.id for user in self.team_members]

    def get_reviews(self):
        return self.project_api.get_user_peer_review_items(
            self.user_id,
            self.group_id,
            self.content_id,
        )


class GradeDisplayStage(FeedbackDisplayBaseStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Grade Display Stage")
    )

    CATEGORY = 'gp-v2-stage-grade-display'
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/grade_display.html'

    STUDIO_LABEL = _(u"Grade Display")
    FEEDBACK_DISPLAY_BLOCK_CATEGORY = GroupProjectGradeEvaluationDisplayXBlock.CATEGORY

    @property
    def allowed_nested_blocks(self):
        blocks = super(GradeDisplayStage, self).allowed_nested_blocks
        blocks.extend([GroupProjectGradeEvaluationDisplayXBlock])
        return blocks

    @lazy
    def final_grade(self):
        """
        Gets final grade for activity
        """
        # this is an expensive computation that can't change in scope of one request - hence lazy. And no, this
        # comment is a very bad docstring.
        return self.activity.calculate_grade(self.group_id)

    def get_reviewer_ids(self):
        return [user['id'] for user in self.project_api.get_workgroup_reviewers(self.group_id, self.content_id)]

    def get_reviews(self):
        return self.project_api.get_workgroup_review_items_for_group(
            self.group_id,
            self.content_id,
        )

    @property
    def can_mark_complete(self):
        base_result = super(GradeDisplayStage, self).can_mark_complete
        if not base_result:
            return False
        return self.final_grade is not None

    def get_stage_content_fragment(self, context, view='student_view'):
        final_grade = self.final_grade
        context_extension = {
            'final_grade': final_grade if final_grade is not None else _(u"N/A")
        }
        context_extension.update(context)
        return super(GradeDisplayStage, self).get_stage_content_fragment(context_extension, view)

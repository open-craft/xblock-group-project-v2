# -*- coding: utf-8 -*-
import logging
import itertools
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import BlockUsageLocator

from django.utils.translation import ugettext as _

from xblock.core import XBlock
from xblock.exceptions import NoSuchUsage
from xblock.fields import Scope, String, Float, Integer
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin

from group_project_v2.mixins import (
    ChildrenNavigationXBlockMixin, WorkgroupAwareXBlockMixin, XBlockWithComponentsMixin, XBlockWithPreviewMixin,
)
from group_project_v2.notifications import ActivityNotificationsMixin
from group_project_v2.project_navigator import GroupProjectNavigatorXBlock
from group_project_v2.utils import loader, make_key, outsider_disallowed_protected_view, get_default_stage
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage,
    STAGE_TYPES
)
from group_project_v2.api_error import ApiError


log = logging.getLogger(__name__)


class GroupProjectXBlock(
    XBlockWithComponentsMixin, ChildrenNavigationXBlockMixin, WorkgroupAwareXBlockMixin,
    XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin
):
    display_name = String(
        display_name="Display Name",
        help="This is a name of the project",
        scope=Scope.settings,
        default="Group Project V2"
    )

    CATEGORY = "gp-v2-project"

    editable_fields = ('display_name', )
    has_score = False
    has_children = True

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return [GroupActivityXBlock, GroupProjectNavigatorXBlock]

    @lazy
    def activities(self):
        all_children = [self.runtime.get_block(child_id) for child_id in self.children]
        return [child for child in all_children if isinstance(child, GroupActivityXBlock)]

    @lazy
    def navigator(self):
        return self.get_child_of_category(GroupProjectNavigatorXBlock.CATEGORY)

    def _get_activity_to_display(self, target_stage_id):
        try:
            if target_stage_id:
                usage_id = BlockUsageLocator.from_string(target_stage_id)
                if usage_id.block_type in STAGE_TYPES:
                    stage = self.runtime.get_block(usage_id)
                    if stage.available_to_current_user:
                        return stage.activity
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        if self.default_stage:
            return self.default_stage.activity

        return self.activities[0] if self.activities else None

    @property
    def default_stage(self):
        default_stages = [activity.default_stage for activity in self.activities]

        return get_default_stage(default_stages)

    @outsider_disallowed_protected_view
    def student_view(self, context):
        target_stage_id = context.get('activate_block_id', None)
        target_activity = self._get_activity_to_display(target_stage_id)

        fragment = Fragment()

        if not target_activity:
            fragment.add_content(_(u"This Group Project does not contain any activities"))
        else:
            activity_fragment = target_activity.render('student_view', context)
            fragment.add_frag_resources(activity_fragment)
            render_context = {
                'project': self,
                'activity_content': activity_fragment.content
            }
            render_context.update(context)
            fragment.add_content(loader.render_template("templates/html/group_project.html", render_context))

        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project.css'))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/group_project.js'))
        fragment.initialize_js("GroupProjectBlock")
        return fragment

    def validate(self):
        validation = super(GroupProjectXBlock, self).validate()

        if not self.has_child_of_category(GroupProjectNavigatorXBlock.CATEGORY):
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Group Project must contain Project Navigator Block")
            ))

        return validation


# TODO: enable and fix these violations
# pylint: disable=unused-argument,invalid-name
@XBlock.wants('notifications')
@XBlock.wants('courseware_parent_info')
class GroupActivityXBlock(
    XBlockWithPreviewMixin, XBlockWithComponentsMixin, ActivityNotificationsMixin,
    XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin,
    ChildrenNavigationXBlockMixin, WorkgroupAwareXBlockMixin
):
    """
    XBlock providing a group activity project for a group of students to collaborate upon
    """
    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Group Project Activity"
    )

    weight = Float(
        display_name="Weight",
        help="This is the maximum score that the user receives when he/she successfully completes the problem",
        scope=Scope.settings,
        default=100.0
    )

    group_reviews_required_count = Integer(
        display_name="Reviews Required Minimum",
        help="The minimum number of group-reviews that should be applied to a set of submissions "
             "(set to 0 to be 'TA Graded')",
        scope=Scope.settings,
        default=3
    )

    user_review_count = Integer(
        display_name="User Reviews Required Minimum",
        help="The minimum number of other-group reviews that an individual user should perform",
        scope=Scope.settings,
        default=1
    )

    CATEGORY = "gp-v2-activity"
    STUDIO_LABEL = _(u"Group Project Activity")

    editable_fields = ("display_name", "weight", "group_reviews_required_count", "user_review_count")
    has_score = True
    has_children = True

    @property
    def id(self):
        return self.scope_ids.usage_id

    @property
    def project(self):
        return self.get_parent()

    @property
    def content_id(self):
        try:
            return unicode(self.scope_ids.usage_id)
        except Exception:  # pylint: disable=broad-except
            return self.id

    @property
    def is_ta_graded(self):
        return self.group_reviews_required_count == 0

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return [
            BasicStage, CompletionStage, SubmissionStage,
            TeamEvaluationStage, PeerReviewStage,
            EvaluationDisplayStage, GradeDisplayStage
        ]

    @property
    def stages(self):
        return self._children

    @property
    def available_stages(self):
        for stage in self.stages:
            if stage.available_to_current_user:
                yield stage

    @property
    def default_stage(self):
        return get_default_stage(self.available_stages)

    @property
    def questions(self):
        return list(itertools.chain(
            *[getattr(stage, 'questions', ()) for stage in self.stages]
        ))

    @property
    def grade_questions(self):
        return list(itertools.chain(
            *[getattr(stage, 'grade_questions', ()) for stage in self.stages]
        ))

    def _get_stage_to_display(self, target_stage_id):
        try:
            if target_stage_id:
                usage_id = BlockUsageLocator.from_string(target_stage_id)
                if usage_id.block_type in STAGE_TYPES:
                    stage = self.runtime.get_block(usage_id)
                    if stage.available_to_current_user:
                        return stage
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        if self.default_stage:
            return self.default_stage

        return self.stages[0] if self.stages else None

    @outsider_disallowed_protected_view
    def student_view(self, context):
        """
        Player view, displayed to the student
        """
        fragment = Fragment()

        target_stage_id = context.get('activate_block_id', None)
        target_stage = self._get_stage_to_display(target_stage_id)

        if not target_stage:
            fragment.add_content(_(u"This Group Project Activity does not contain any stages"))
        else:
            stage_fragment = target_stage.render('student_view', context)
            fragment.add_frag_resources(stage_fragment)
            render_context = {
                'activity': self,
                'stage_content': stage_fragment.content,
            }
            render_context.update(context)
            fragment.add_content(loader.render_template('/templates/html/activity/student_view.html', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def navigation_view(self, context):
        fragment = Fragment()

        target_stage_id = context.get('activate_block_id', None)
        if not target_stage_id:
            target_stage = self.project.default_stage
            if target_stage:
                target_stage_id = str(target_stage.id)

        children_context = {BasicStage.CURRENT_STAGE_ID_PARAMETER_NAME: target_stage_id}
        children_context.update(context)

        stage_contents = []
        for stage in self.available_stages:
            child_fragment = stage.render('navigation_view', children_context)
            fragment.add_frag_resources(child_fragment)
            stage_contents.append(child_fragment.content)

        context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(loader.render_template("templates/html/activity/navigation_view.html", context))

        return fragment

    @outsider_disallowed_protected_view
    def resources_view(self, context):
        fragment = Fragment()

        has_resources = any([bool(stage.resources) for stage in self.stages])

        stage_contents = []
        for child in self.stages:
            child_fragment = child.render('resources_view', context)
            fragment.add_frag_resources(child_fragment)
            stage_contents.append(child_fragment.content)

        context = {'activity': self, 'stage_contents': stage_contents, 'has_resources': has_resources}
        fragment.add_content(loader.render_template("templates/html/activity/resources_view.html", context))

        return fragment

    @outsider_disallowed_protected_view
    def submissions_view(self, context):
        fragment = Fragment()

        target_stages = [stage for stage in self.stages if isinstance(stage, SubmissionStage)]

        has_submissions = any([stage.has_submissions for stage in target_stages])

        submission_contents = []
        for stage in target_stages:
            for child in stage.submissions:
                child_fragment = child.render('submissions_view', context)
                fragment.add_frag_resources(child_fragment)
                submission_contents.append(child_fragment.content)

        context = {'activity': self, 'submission_contents': submission_contents, 'has_submissions': has_submissions}
        fragment.add_content(loader.render_template("templates/html/activity/submissions_view.html", context))

        return fragment

    def mark_complete(self, user_id):
        try:
            self.project_api.mark_as_complete(self.course_id, self.content_id, user_id)
        except ApiError as e:
            # 409 indicates that the completion record already existed. That's ok in this case
            if e.code != 409:
                raise

    def validate_field_data(self, validation, data):
        super(GroupActivityXBlock, self).validate_field_data(validation, data)
        should_be_ints = ('weight', 'group_reviews_required_count', 'user_review_count')
        for field_name in should_be_ints:
            try:
                int(getattr(data, field_name))
            except (TypeError, ValueError):
                message = _(u"{field_name} must be integer, {field_value} given").format(
                    field_name=field_name, field_value=getattr(data, field_name)
                )
                validation.add(ValidationMessage(ValidationMessage.ERROR, message))

    def calculate_and_send_grade(self, group_id):
        grade_value = self.calculate_grade(group_id)
        if grade_value:
            self.assign_grade_to_group(group_id, grade_value)

            workgroup = self.project_api.get_workgroup_by_id(group_id)
            for u in workgroup["users"]:
                self.mark_complete(u["id"])

    def assign_grade_to_group(self, group_id, grade_value):
        self.project_api.set_group_grade(
            group_id,
            self.course_id,
            self.content_id,
            grade_value,
            self.weight
        )
        # Emit analytics event...
        self.runtime.publish(
            self,
            "group_activity.final_grade",
            {
                "grade_value": grade_value,
                "group_id": group_id,
                "content_id": self.content_id,
            }
        )
        self.runtime.publish(self, 'grade', {
            'value': grade_value,
            'max_value': self.weight,
        })
        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            self.fire_grades_posted_notification(group_id, notifications_service)

    def calculate_grade(self, group_id):  # pylint:disable=too-many-locals,too-many-branches

        def mean(value_array):
            numeric_values = [float(v) for v in value_array]
            return float(sum(numeric_values) / len(numeric_values))

        review_item_data = self.project_api.get_workgroup_review_items_for_group(group_id, self.content_id)
        review_item_map = {
            make_key(review_item['question'], self.real_user_id(review_item['reviewer'])): review_item['answer']
            for review_item in review_item_data
        }
        all_reviewer_ids = set([self.real_user_id(review_item['reviewer']) for review_item in review_item_data])
        group_reviewer_ids = [
            user["id"] for user in self.project_api.get_workgroup_reviewers(group_id, self.content_id)
        ]
        admin_reviewer_ids = [reviewer_id for reviewer_id in all_reviewer_ids if reviewer_id not in group_reviewer_ids]

        def get_user_grade_value_list(user_id):
            user_grades = []
            for question in self.grade_questions:
                user_value = review_item_map.get(make_key(question.question_id, user_id), None)
                if user_value is None:
                    # if any are incomplete, we consider the whole set to be unusable
                    return None
                else:
                    user_grades.append(user_value)

            return user_grades

        admin_provided_grades = None
        if len(admin_reviewer_ids) > 0:
            admin_provided_grades = []
            # Only include complete admin gradesets
            admin_reviewer_grades = [
                arg
                for arg in [get_user_grade_value_list(admin_id) for admin_id in admin_reviewer_ids]
                if arg
            ]
            admin_grader_count = len(admin_reviewer_grades)
            if admin_grader_count > 1:
                for idx in range(len(self.grade_questions)):
                    admin_provided_grades.append(mean([adm[idx] for adm in admin_reviewer_grades]))
            elif admin_grader_count > 0:  # which actually means admin_grader_count == 1
                admin_provided_grades = admin_reviewer_grades[0]

        user_grades = {}
        if len(group_reviewer_ids) > 0:
            for reviewer_id in group_reviewer_ids:
                this_reviewers_grades = get_user_grade_value_list(reviewer_id)
                if this_reviewers_grades is None:
                    if admin_provided_grades:
                        this_reviewers_grades = admin_provided_grades
                    else:
                        return None
                user_grades[reviewer_id] = this_reviewers_grades
        elif admin_provided_grades:
            group_reviewer_ids = [self.user_id]
            user_grades[self.user_id] = admin_provided_grades
        else:
            return None

        # Okay, if we've got here we have a complete set of marks to calculate the grade
        reviewer_grades = [
            mean(user_grades[reviewer_id])
            for reviewer_id in group_reviewer_ids
            if len(user_grades[reviewer_id]) > 0
        ]
        group_grade = round(mean(reviewer_grades)) if len(reviewer_grades) > 0 else None

        return group_grade

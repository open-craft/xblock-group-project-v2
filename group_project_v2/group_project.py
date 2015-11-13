# -*- coding: utf-8 -*-
import logging
import itertools
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError

from xblock.core import XBlock
from xblock.exceptions import NoSuchUsage
from xblock.fields import Scope, String, Float, Integer, DateTime
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.studio_editable import XBlockWithPreviewMixin, NestedXBlockSpec

from group_project_v2.mixins import CommonMixinCollection
from group_project_v2.notifications import ActivityNotificationsMixin
from group_project_v2.project_navigator import GroupProjectNavigatorXBlock
from group_project_v2.utils import (
    mean, make_key, outsider_disallowed_protected_view, get_default_stage, DiscussionXBlockShim, Constants,
    add_resource, gettext as _
)
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage,
    STAGE_TYPES
)


log = logging.getLogger(__name__)


class GroupProjectXBlock(CommonMixinCollection, XBlock):
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

    template_location = "project"

    @staticmethod
    def _sanitize_context(context):
        """
        Context passed into views is :class:QueryDict instance, which has a particular feature of supporting multiple
        values for the same key. It is achieved at a cost of always using lists even for singular values. When `get` is
        invoked for the singular key it detects there's only one value and returns value, not the list itself

        The caveat is that if it is used with dict(context) or update(context), those singular values are returned as
        lists. This breaks the approach of passing context as intact as possible to children by making a copy and adding
        necessary children data. So, this method serves as a filter and converter for context coming from LMS.
        """
        if not context:
            return {}

        return {
            Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: context.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME, None)
        }

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        return [
            NestedXBlockSpec(GroupActivityXBlock),
            NestedXBlockSpec(GroupProjectNavigatorXBlock, single_instance=True),
            NestedXBlockSpec(DiscussionXBlockShim, single_instance=True)
        ]

    @lazy
    def activities(self):
        all_children = [self.runtime.get_block(child_id) for child_id in self.children]
        return [child for child in all_children if isinstance(child, GroupActivityXBlock)]

    @lazy
    def navigator(self):
        return self.get_child_of_category(GroupProjectNavigatorXBlock.CATEGORY)

    def get_stage_to_display(self, target_block_id):
        try:
            if target_block_id:
                target_block = self.runtime.get_block(target_block_id)
                if self.get_child_category(target_block) in STAGE_TYPES and target_block.available_to_current_user:
                    return target_block
                if isinstance(target_block, GroupActivityXBlock):
                    return target_block.default_stage
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        default_stage = self.default_stage
        if default_stage:
            return default_stage

        if self.activities:
            return self.activities[0].get_stage_to_display(target_block_id)

        return None  # if there are no activities there's no stages as well - nothing we can really do

    @property
    def default_stage(self):
        default_stages = [activity.default_stage for activity in self.activities]

        return get_default_stage(default_stages)

    @outsider_disallowed_protected_view
    def student_view(self, context):
        ctx = self._sanitize_context(context)

        fragment = Fragment()
        render_context = {
            'project': self,
            'course_id': self.course_id,
            'group_id': self.workgroup['id']
        }

        render_context.update(context)

        def render_child_fragment(child, content_key, fallback_message, extra_context=None):
            """
            Renders child, appends child fragment resources to parent fragment and
            updates parent's rendering context
            """
            internal_context = dict(ctx)
            if extra_context:
                internal_context.update(extra_context)

            if child:
                log.debug("Rendering {child} with context: {context}".format(
                    child=child.__class__.__name__, context=internal_context,
                ))
                child_fragment = child.render('student_view', internal_context)
                fragment.add_frag_resources(child_fragment)
                render_context[content_key] = child_fragment.content
            else:
                render_context[content_key] = fallback_message

        target_block_id = self.get_block_id_from_string(ctx.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME, None))
        target_stage = self.get_stage_to_display(target_block_id)

        child_context = {}
        if target_stage:
            child_context[Constants.CURRENT_STAGE_ID_PARAMETER_NAME] = target_stage.id

        # activity should be rendered first, as some stages might report completion in student-view - this way stage
        # PN sees updated state.
        target_activity = target_stage.activity if target_stage else None
        render_child_fragment(
            target_activity, 'activity_content', _(u"This Group Project does not contain any activities"),
            child_context
        )

        # TODO: project nav is slow, mostly due to navigation view. It might make sense to rework it into
        # asynchronously loading navigation and stage states.
        project_navigator = self.get_child_of_category(GroupProjectNavigatorXBlock.CATEGORY)
        render_child_fragment(
            project_navigator, 'project_navigator_content',
            _(u"This Group Project V2 does not contain Project Navigator - "
              u"please edit course outline in Studio to include one"),
            child_context
        )

        discussion = self.get_child_of_category(DiscussionXBlockShim.CATEGORY)
        render_child_fragment(
            discussion, 'discussion_content',
            _(u"This Group Project V2 does not contain a discussion"),
            child_context
        )

        fragment.add_content(self.render_template('student_view', render_context))

        add_resource(self, 'css', 'public/css/group_project.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)
        add_resource(self, 'javascript', 'public/js/group_project.js', fragment)
        fragment.initialize_js("GroupProjectBlock")
        return fragment

    def dashboard_view(self, context):
        fragment = Fragment()

        activity_fragments = self._render_children('dashboard_view', context, self.activities)
        activity_contents = [frag.content for frag in activity_fragments]
        fragment.add_frags_resources(activity_fragments)

        render_context = {'project': self, 'activity_contents': activity_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))
        add_resource(self, 'css', 'public/css/group_project_dashboard.css', fragment)

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
class GroupActivityXBlock(CommonMixinCollection, XBlockWithPreviewMixin, ActivityNotificationsMixin, XBlock):
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

    due_date = DateTime(
        display_name="Due date",
        help="ACtivity due date",
        has_score=Scope.settings,
        default=None
    )

    CATEGORY = "gp-v2-activity"
    STUDIO_LABEL = _(u"Group Project Activity")

    editable_fields = ("display_name", "weight", "group_reviews_required_count", "user_review_count", "due_date")
    has_score = True
    has_children = True

    template_location = 'activity'

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
        def_stage = get_default_stage(self.available_stages)
        if def_stage:
            return def_stage
        else:
            return self.stages[0] if self.stages else None

    @property
    def questions(self):
        return list(self._chain_questions(self.stages, 'questions'))

    @property
    def grade_questions(self):
        return list(self._chain_questions(self.stages, 'grade_questions'))

    @property
    def team_evaluation_questions(self):
        stages = self.get_children_by_category(TeamEvaluationStage.CATEGORY)
        return list(self._chain_questions(stages, 'questions'))

    @property
    def peer_review_questions(self):
        stages = self.get_children_by_category(PeerReviewStage.CATEGORY)
        return list(self._chain_questions(stages, 'questions'))

    @staticmethod
    def _chain_questions(stages, question_type):
        return itertools.chain.from_iterable(getattr(stage, question_type, ()) for stage in stages)

    def get_stage_to_display(self, target_block_id):
        try:
            if target_block_id:
                stage = self.runtime.get_block(target_block_id)
                if self.get_child_category(stage) in STAGE_TYPES and stage.available_to_current_user:
                    return stage
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        return self.default_stage

    @outsider_disallowed_protected_view
    def student_view(self, context):
        """
        Player view, displayed to the student
        """
        fragment = Fragment()

        current_stage_id = context.get(Constants.CURRENT_STAGE_ID_PARAMETER_NAME, None)
        target_stage = self.get_stage_to_display(current_stage_id)

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
            fragment.add_content(self.render_template('student_view', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def navigation_view(self, context):
        fragment = Fragment()

        children_context = {}
        children_context.update(context)

        stage_fragments = self._render_children('navigation_view', children_context, self.available_stages)
        stage_contents = [frag.content for frag in stage_fragments]
        fragment.add_frags_resources(stage_fragments)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template('navigation_view', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def resources_view(self, context):
        fragment = Fragment()

        resources = [resource for stage in self.stages for resource in stage.resources]
        has_resources = bool(resources)

        resource_fragments = self._render_children('resources_view', context, resources)
        resource_contents = [frag.content for frag in resource_fragments]
        fragment.add_frags_resources(resource_fragments)

        render_context = {'activity': self, 'resource_contents': resource_contents, 'has_resources': has_resources}
        fragment.add_content(self.render_template('resources_view', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def submissions_view(self, context):
        fragment = Fragment()

        submissions = [
            submission
            for stage in self.stages if isinstance(stage, SubmissionStage)
            for submission in stage.submissions
        ]
        has_submissions = bool(submissions)

        submission_fragments = self._render_children('submissions_view', context, submissions)
        submission_contents = [frag.content for frag in submission_fragments]
        fragment.add_frags_resources(submission_fragments)

        render_context = {'activity': self, 'submission_contents': submission_contents, 'has_submissions': has_submissions}
        fragment.add_content(self.render_template('submissions_view', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def dashboard_view(self, context):
        fragment = Fragment()

        stage_fragments = self._render_children('dashboard_view', context, self.available_stages)
        stage_contents = [frag.content for frag in stage_fragments]
        fragment.add_frags_resources(stage_fragments)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))

        return fragment

    def mark_complete(self, user_id):
        self.runtime.publish(self, 'progress', {'user_id': user_id})

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
                self.runtime.publish(self, 'grade', {
                    'user_id': u["id"],
                    'value': grade_value,
                    'max_value': self.weight,
                })

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

        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            self.fire_grades_posted_notification(group_id, notifications_service)

    def calculate_grade(self, group_id):  # pylint:disable=too-many-locals,too-many-branches
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

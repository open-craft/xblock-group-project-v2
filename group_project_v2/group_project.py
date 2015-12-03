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

from group_project_v2 import messages
from group_project_v2.mixins import CommonMixinCollection, DashboardXBlockMixin, DashboardRootXBlockMixin
from group_project_v2.notifications import ActivityNotificationsMixin
from group_project_v2.project_navigator import GroupProjectNavigatorXBlock
from group_project_v2.utils import (
    mean, make_key, outsider_disallowed_protected_view, get_default_stage, DiscussionXBlockShim, Constants,
    add_resource, gettext as _, get_block_content_id
)
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage,
    STAGE_TYPES
)

log = logging.getLogger(__name__)


class GroupProjectXBlock(CommonMixinCollection, DashboardXBlockMixin, DashboardRootXBlockMixin, XBlock):
    display_name = String(
        display_name=_(u"Display Name"),
        help=_(u"This is a name of the project"),
        scope=Scope.settings,
        default=_(u"Group Project V2")
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

    @property
    def content_id(self):
        return get_block_content_id(self)

    @property
    def project_details(self):
        return self.project_api.get_project_by_content_id(self.course_id, self.content_id)

    @lazy
    def activities(self):
        all_children = [self.runtime.get_block(child_id) for child_id in self.children]
        return [child for child in all_children if isinstance(child, GroupActivityXBlock)]

    @lazy
    def navigator(self):
        return self.get_child_of_category(GroupProjectNavigatorXBlock.CATEGORY)

    @property
    def default_stage(self):
        default_stages = [activity.default_stage for activity in self.activities]

        return get_default_stage(default_stages)

    @staticmethod
    def _render_child_fragment_with_fallback(child, context, fallback_message, view='student_view'):
        if child:
            log.debug("Rendering {child} with context: {context}".format(
                child=child.__class__.__name__, context=context,
            ))
            return child.render(view, context)
        else:
            return Fragment(fallback_message)

    @outsider_disallowed_protected_view
    def student_view(self, context):
        ctx = self._sanitize_context(context)

        fragment = Fragment()
        render_context = {
            'project': self,
            'course_id': self.course_id,
            'group_id': self.workgroup.id
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

            child_fragment = self._render_child_fragment_with_fallback(
                child, internal_context, fallback_message, 'student_view'
            )
            fragment.add_frag_resources(child_fragment)
            render_context[content_key] = child_fragment.content

        target_block_id = self.get_block_id_from_string(ctx.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME, None))
        target_stage = self.get_stage_to_display(target_block_id)

        child_context = {}
        if target_stage:
            child_context[Constants.CURRENT_STAGE_ID_PARAMETER_NAME] = target_stage.id

        # activity should be rendered first, as some stages might report completion in student-view - this way stage
        # PN sees updated state.
        target_activity = target_stage.activity if target_stage else None
        render_child_fragment(target_activity, 'activity_content', messages.NO_ACTIVITIES, child_context)

        # TODO: project nav is slow, mostly due to navigation view. It might make sense to rework it into
        # asynchronously loading navigation and stage states.
        project_navigator = self.get_child_of_category(GroupProjectNavigatorXBlock.CATEGORY)
        render_child_fragment(
            project_navigator, 'project_navigator_content', messages.NO_PROJECT_NAVIGATOR, child_context
        )

        discussion = self.get_child_of_category(DiscussionXBlockShim.CATEGORY)
        render_child_fragment(discussion, 'discussion_content', messages.NO_DISCUSSION, child_context)

        fragment.add_content(self.render_template('student_view', render_context))

        add_resource(self, 'css', 'public/css/group_project.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_common.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)
        add_resource(self, 'javascript', 'public/js/group_project.js', fragment)
        fragment.initialize_js("GroupProjectBlock")
        return fragment

    def dashboard_view(self, context):
        fragment = Fragment()

        children_context = context.copy()
        self._append_context_parameters_if_not_present(children_context)

        activity_fragments = self._render_children('dashboard_view', children_context, self.activities)
        activity_contents = [frag.content for frag in activity_fragments]
        fragment.add_frags_resources(activity_fragments)

        render_context = {'project': self, 'activity_contents': activity_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))
        add_resource(self, 'css', 'public/css/group_project_common.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_dashboard.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)

        return fragment

    def dashboard_detail_view(self, context):
        ctx = self._sanitize_context(context)

        fragment = Fragment()
        render_context = {
            'project': self,
            'course_id': self.course_id,
            'group_id': self.workgroup.id
        }

        render_context.update(ctx)

        target_block_id = self.get_block_id_from_string(ctx.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME, None))
        target_activity = self._get_target_block(target_block_id)
        if target_activity is None and self.activities:
            target_activity = self.activities[0]

        activity_fragment = self._render_child_fragment_with_fallback(
            target_activity, ctx, messages.NO_ACTIVITIES, view='dashboard_detail_view'
        )
        render_context['activity_content'] = activity_fragment.content
        fragment.add_frag_resources(activity_fragment)

        fragment.add_content(self.render_template('dashboard_detail_view', render_context))
        add_resource(self, 'css', 'public/css/group_project_common.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_dashboard.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)

        return fragment

    def validate(self):
        validation = super(GroupProjectXBlock, self).validate()

        if not self.has_child_of_category(GroupProjectNavigatorXBlock.CATEGORY):
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                messages.MUST_CONTAIN_PROJECT_NAVIGATOR_BLOCK
            ))

        return validation

    def _get_target_block(self, target_block_id):
        try:
            if target_block_id:
                return self.runtime.get_block(target_block_id)
        except (InvalidKeyError, KeyError, NoSuchUsage) as exc:
            log.exception(exc)

        return None

    def get_stage_to_display(self, target_block_id):
        target_block = self._get_target_block(target_block_id)
        if target_block is not None:
            if self.get_child_category(target_block) in STAGE_TYPES and target_block.available_to_current_user:
                return target_block
            if isinstance(target_block, GroupActivityXBlock):
                return target_block.default_stage

        default_stage = self.default_stage
        if default_stage:
            return default_stage

        if self.activities:
            return self.activities[0].get_stage_to_display(target_block_id)

        return None  # if there are no activities there's no stages as well - nothing we can really do


@XBlock.wants('notifications')
@XBlock.wants('courseware_parent_info')
@XBlock.wants('settings')
class GroupActivityXBlock(
    CommonMixinCollection, DashboardXBlockMixin, DashboardRootXBlockMixin,
    XBlockWithPreviewMixin, ActivityNotificationsMixin, XBlock
):
    """
    XBlock providing a group activity project for a group of students to collaborate upon
    """
    display_name = String(
        display_name=_(u"Display Name"),
        help=_(u"This name appears in the horizontal navigation at the top of the page."),
        scope=Scope.settings,
        default=_(u"Group Project Activity")
    )

    weight = Float(
        display_name=_(u"Weight"),
        help=_(u"This is the maximum score that the user receives when he/she successfully completes the problem."),
        scope=Scope.settings,
        default=100.0
    )

    group_reviews_required_count = Integer(
        display_name=_(u"Reviews Required Minimum"),
        help=_(u"The minimum number of group-reviews that should be applied to a set of submissions "
               u"(set to 0 to be 'TA Graded')"),
        scope=Scope.settings,
        default=3
    )

    user_review_count = Integer(
        display_name=_(u"User Reviews Required Minimum"),
        help=_(u"The minimum number of other-group reviews that an individual user should perform"),
        scope=Scope.settings,
        default=1
    )

    due_date = DateTime(
        display_name=_(u"Due date"),
        help=_(u"Activity due date"),
        has_score=Scope.settings,
        default=None
    )

    CATEGORY = "gp-v2-activity"
    STUDIO_LABEL = _(u"Group Project Activity")

    editable_fields = ("display_name", "weight", "group_reviews_required_count", "user_review_count", "due_date")
    has_score = True
    has_children = True

    template_location = 'activity'

    DASHBOARD_DETAILS_URL_KEY = 'dashboard_details_url'
    DEFAULT_DASHBOARD_DETAILS_URL_TPL = "/dashboard_details_view?activate_block_id={activity_id}"

    @property
    def id(self):
        return self.scope_ids.usage_id

    def max_score(self):
        """
        Used for grading purposes:
            * As max grade for submitting grade event. See :method:`assign_grade_to_group`
            * As theoretical max score for grade calculation when grade is not yet available
        :rtype: Float
        """
        return self.weight

    @property
    def project(self):
        return self.get_parent()

    @property
    def content_id(self):
        return get_block_content_id(self)

    @property
    def project_details(self):
        # Project is linked to top-level GroupProjectXBlock, not individual Activities
        return self.project.project_details

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

    def dashboard_details_url(self):
        """
        Gets dashboard details view URL for current activity. If settings service is not available or does not provide
        URL template, default template is used.
        """
        template = self.DEFAULT_DASHBOARD_DETAILS_URL_TPL
        settings_service = self.runtime.service(self, "settings")
        if settings_service:
            xblock_settings = settings_service.get_settings_bucket(self)
            if xblock_settings and self.DASHBOARD_DETAILS_URL_KEY in xblock_settings:
                template = xblock_settings[self.DASHBOARD_DETAILS_URL_KEY]

        return template.format(
            program_id=self.user_preferences.get(self.DASHBOARD_PROGRAM_ID_KEY, None),
            course_id=self.course_id, project_id=self.project.scope_ids.usage_id, activity_id=self.id
        )

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
            fragment.add_content(messages.NO_STAGES)
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

        render_context = {
            'activity': self, 'submission_contents': submission_contents, 'has_submissions': has_submissions
        }
        fragment.add_content(self.render_template('submissions_view', render_context))

        return fragment

    def _render_dashboard_view(self, context, view):
        fragment = Fragment()

        children_context = context.copy()
        self._append_context_parameters_if_not_present(children_context)

        stage_fragments = self._render_children(view, children_context, self.stages)
        stage_contents = [frag.content for frag in stage_fragments]
        fragment.add_frags_resources(stage_fragments)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template(view, render_context))

        return fragment

    @outsider_disallowed_protected_view
    def dashboard_view(self, context):
        fragment = Fragment()

        children_context = context.copy()
        self._append_context_parameters_if_not_present(children_context)

        stage_fragments = self._render_children('dashboard_view', children_context, self.stages)
        stage_contents = [frag.content for frag in stage_fragments]
        fragment.add_frags_resources(stage_fragments)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))

        return fragment

    @outsider_disallowed_protected_view
    def dashboard_detail_view(self, context):
        fragment = Fragment()

        children_context = context.copy()
        self._append_context_parameters_if_not_present(children_context)

        target_stages = [stage for stage in self.stages if stage.is_graded_stage]
        stage_fragments = self._render_children('dashboard_detail_view', children_context, target_stages)

        stages = []
        for stage in target_stages:
            fragment = stage.render('dashboard_detail_view', children_context)
            fragment.add_frags_resources(stage_fragments)
            stages.append({"id": stage.id, 'content': fragment.content})

        groups_data = [
            {
                'id': 1, 'name': 'Group 1', 'stages': {stage.id: 'incomplete' for stage in target_stages},
                'users': [
                    {
                        'full_name': "John Doe", 'email': "john_doe@examle.com",
                        'stages': {stage.id: 'incomplete' for stage in target_stages}
                    },
                    {
                        'full_name': "Jane Doe", 'email': "jane_doe@examle.com",
                        'stages': {stage.id: 'incomplete' for stage in target_stages}
                    },
                ]
            },
            {
                'id': 2, 'name': 'Group 2', 'stages': {stage.id: 'incomplete' for stage in target_stages},
                'users': [
                    {
                        'full_name': "Jack Doe", 'email': "jack_doe@examle.com",
                        'stages': {stage.id: 'incomplete' for stage in target_stages}
                    },
                ]
            }
        ]
        stage_cell_width_percent = (100-30) / float(len(target_stages))

        render_context = {
            'activity': self, 'stages': stages, 'stages_count': len(stages), 'groups': groups_data,
            'cell_width_percent': stage_cell_width_percent,
            'assigned_to_groups_label': messages.ASSIGNED_TO_GROUPS_LABEL.format(group_count=len(groups_data))
        }
        fragment.add_content(self.render_template('dashboard_detail_view', render_context))

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
            for user in workgroup.users:
                self.mark_complete(user.id)

    def assign_grade_to_group(self, group_id, grade_value):
        """
        Assigns grade to group, fires required events and notifications
        :param int group_id: Group ID
        :param float grade_value: Grade to assign
        :return:
        """
        self.project_api.set_group_grade(
            group_id,
            self.course_id,
            self.content_id,
            grade_value,
            self.max_score()
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

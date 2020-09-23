# -*- coding: utf-8 -*-
from builtins import range
import logging
import itertools
from operator import itemgetter
from datetime import datetime

import webob
from lazy.lazy import lazy
from opaque_keys import InvalidKeyError
from xblock.core import XBlock
from xblock.exceptions import NoSuchUsage
from xblock.fields import Scope, String, Float, Integer, DateTime
from xblock.validation import ValidationMessage
from web_fragments.fragment import Fragment
from xblockutils.studio_editable import XBlockWithPreviewMixin, NestedXBlockSpec

from group_project_v2 import messages
from group_project_v2.mixins import (
    CommonMixinCollection, DashboardXBlockMixin, DashboardRootXBlockMixin,
    AuthXBlockMixin
)
from group_project_v2.project_navigator import GroupProjectNavigatorXBlock
from group_project_v2.stage.utils import StageState
from group_project_v2.utils import (
    mean, make_key, groupwork_protected_view, get_default_stage, DiscussionXBlockShim, Constants,
    add_resource, gettext as _, get_block_content_id, export_to_csv, named_tuple_with_docstring
)
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage,
    STAGE_TYPES
)

log = logging.getLogger(__name__)


@XBlock.wants("settings")
class GroupProjectXBlock(CommonMixinCollection, DashboardXBlockMixin, DashboardRootXBlockMixin, XBlock):
    display_name = String(
        display_name=_(u"Display Name"),
        help=_(u"This is a name of the project"),
        scope=Scope.settings,
        default=_(u"Group Project V2")
    )

    CATEGORY = "gp-v2-project"
    REPORT_FILENAME = "group_project_{group_project_name}_stage_{stage_name}_incomplete_report_{timestamp}.csv"
    CSV_HEADERS = ['Name', 'Username', 'Email']
    CSV_TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"

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
        raw_client_id = context.get(Constants.CURRENT_CLIENT_FILTER_ID_PARAMETER_NAME)
        client_id = None
        if raw_client_id is not None and raw_client_id.strip():
            client_id = int(raw_client_id)
        return {
            Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: context.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME, None),
            Constants.CURRENT_CLIENT_FILTER_ID_PARAMETER_NAME: client_id
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
        # pylint: disable=logging-format-interpolation
        if child:
            log.debug("Rendering {child} with context: {context}".format(
                child=child.__class__.__name__, context=context,
            ))
            return child.render(view, context)
        return Fragment(fallback_message)

    @groupwork_protected_view
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
            fragment.add_fragment_resources(child_fragment)
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
        add_resource(self, 'javascript', 'public/js/group_project_common.js', fragment)
        fragment.initialize_js("GroupProjectBlock")
        return fragment

    @groupwork_protected_view
    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_view(self, context):
        fragment = Fragment()

        children_context = self._sanitize_context(context)
        self._add_students_and_workgroups_to_context(children_context)

        activity_fragments = self._render_children('dashboard_view', children_context, self.activities)
        activity_contents = [frag.content for frag in activity_fragments]
        for activity_fragment in activity_fragments:
            fragment.add_fragment_resources(activity_fragment)

        render_context = {'project': self, 'activity_contents': activity_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))
        add_resource(self, 'css', 'public/css/group_project_common.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_dashboard.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)

        return fragment

    @groupwork_protected_view
    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_detail_view(self, context):
        ctx = self._sanitize_context(context)
        self._add_students_and_workgroups_to_context(ctx)

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
        fragment.add_fragment_resources(activity_fragment)

        fragment.add_content(self.render_template('dashboard_detail_view', render_context))
        add_resource(self, 'css', 'public/css/group_project_common.css', fragment)
        add_resource(self, 'css', 'public/css/group_project_dashboard.css', fragment)
        add_resource(self, 'css', 'public/css/vendor/font-awesome/font-awesome.css', fragment, via_url=True)
        add_resource(self, 'javascript', 'public/js/group_project_dashboard_detail.js', fragment)

        fragment.initialize_js('GroupProjectBlockDashboardDetailsView')

        return fragment

    @XBlock.handler
    def download_incomplete_list(self, request, _suffix=''):
        target_stage_id = self.get_block_id_from_string(request.GET.get(Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME))
        target_stage = self._get_target_block(target_stage_id)

        if target_stage is None:
            return webob.response.Response(u"Stage {stage_id} not found".format(stage_id=target_stage_id), status=404)

        workgroups, users = self.get_workgroups_and_students()
        completed, _partially_completed = target_stage.get_users_completion(workgroups, users)

        users_to_export = [user for user in users if user.id not in completed]
        filename = self.REPORT_FILENAME.format(
            group_project_name=self.display_name, stage_name=target_stage.display_name,
            timestamp=datetime.utcnow().strftime(self.CSV_TIMESTAMP_FORMAT)
        )

        return self.export_users(users_to_export, filename)

    @classmethod
    def export_users(cls, users_to_export, filename):
        response = webob.response.Response(charset='UTF-8', content_type="text/csv")
        response.headers['Content-Disposition'] = 'attachment; filename="{filename}"'.format(filename=filename)
        user_data = [[user.full_name, user.username, user.email] for user in users_to_export]
        export_to_csv(user_data, response, headers=cls.CSV_HEADERS)

        return response

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


StageCompletionDetailsData = named_tuple_with_docstring(  # pylint: disable=invalid-name
    "StageCompletionDetailsData",
    ['internal_group_status', 'external_group_status', 'external_group_status_label', 'user_stats', 'groups_to_grade'],
    """
    StageCompletionDetailsData members
    * internal_group_status: dict[group_id, StageState] - group-wise internal completion status - aggregate
        of individual student statuses
    * external_group_status: dict[group_id, StageState] - group-wise external completion status. Not all stages
        have external statuses, see stage's get_external_group_status for meaning of external status.
    * user_stats: dict[user_id, StageState] - user-wise completion
    * groups_to_grade: dict[user_id, list[{'id': group_id}] - groups to review for each user
    """
)


@XBlock.wants('notifications')
@XBlock.wants('courseware_parent_info')
@XBlock.wants('settings')
class GroupActivityXBlock(
        CommonMixinCollection, DashboardXBlockMixin,
        XBlockWithPreviewMixin, XBlock
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
    TA_REVIEW_URL_KEY = 'ta_review_url'
    DEFAULT_TA_REVIEW_URL_TPL = "ta_grading=true&activate_block_id={activate_block_id}&group_id={group_id}"

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

    @property
    def grade_display_stages(self):
        return self.get_children_by_category(GradeDisplayStage.CATEGORY)

    def get_grade_display_stage(self):
        """
        returns grade display stage with max open date.
        """
        stages = self.grade_display_stages
        if stages:
            grade_display_stage = max(stages, key=lambda stage: stage.open_date if stage.open_date else datetime.min)
        else:
            grade_display_stage = None
        return grade_display_stage

    def dashboard_details_url(self):
        """
        Gets dashboard details view URL for current activity. If settings service is not available or does not provide
        URL template, default template is used.
        """
        template = self._get_setting(self.DASHBOARD_DETAILS_URL_KEY, self.DEFAULT_DASHBOARD_DETAILS_URL_TPL)

        return template.format(
            program_id=self.user_preferences.get(self.DASHBOARD_PROGRAM_ID_KEY, None),
            course_id=self.course_id, project_id=self.project.scope_ids.usage_id, activity_id=self.id
        )

    def get_ta_review_link(self, group_id, target_block_id=None):
        target_block_id = target_block_id if target_block_id else self.id
        template = self._get_setting(self.TA_REVIEW_URL_KEY, self.DEFAULT_TA_REVIEW_URL_TPL)
        return template.format(course_id=self.course_id, group_id=group_id, activate_block_id=target_block_id)

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

    @groupwork_protected_view
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
            fragment.add_fragment_resources(stage_fragment)
            render_context = {
                'activity': self,
                'stage_content': stage_fragment.content,
            }
            render_context.update(context)
            fragment.add_content(self.render_template('student_view', render_context))

        return fragment

    @groupwork_protected_view
    def navigation_view(self, context):
        fragment = Fragment()

        children_context = {}
        children_context.update(context)

        stage_fragments = self._render_children('navigation_view', children_context, self.available_stages)
        stage_contents = [frag.content for frag in stage_fragments]
        for stage_fragment in stage_fragments:
            fragment.add_fragment_resources(stage_fragment)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template('navigation_view', render_context))

        return fragment

    @groupwork_protected_view
    def resources_view(self, context):
        fragment = Fragment()

        resources = [resource for stage in self.stages for resource in stage.resources]
        has_resources = bool(resources)

        resource_fragments = self._render_children('resources_view', context, resources)
        resource_contents = [frag.content for frag in resource_fragments]
        for resource_fragment in resource_fragments:
            fragment.add_fragment_resources(resource_fragment)

        render_context = {'activity': self, 'resource_contents': resource_contents, 'has_resources': has_resources}
        fragment.add_content(self.render_template('resources_view', render_context))

        return fragment

    @groupwork_protected_view
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
        for submission_fragment in submission_fragments:
            fragment.add_fragment_resources(submission_fragment)

        render_context = {
            'activity': self, 'submission_contents': submission_contents, 'has_submissions': has_submissions
        }
        fragment.add_content(self.render_template('submissions_view', render_context))

        return fragment

    @groupwork_protected_view
    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_view(self, context):
        fragment = Fragment()

        children_context = context.copy()

        stage_fragments = self._render_children('dashboard_view', children_context, self.stages)
        stage_contents = [frag.content for frag in stage_fragments]
        for stage_fragment in stage_fragments:
            fragment.add_fragment_resources(stage_fragment)

        render_context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(self.render_template('dashboard_view', render_context))

        return fragment

    @groupwork_protected_view
    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_detail_view(self, context):
        fragment = Fragment()

        children_context = context.copy()

        target_workgroups = context.get(Constants.TARGET_WORKGROUPS)
        target_users = context.get(Constants.TARGET_STUDENTS)
        filtered_users = children_context[Constants.FILTERED_STUDENTS]

        stages = []
        stage_stats = {}
        for stage in self.stages:
            if not stage.shown_on_detail_view:
                continue
            stage_fragment = stage.render('dashboard_detail_view', children_context)
            stage_fragment.add_fragment_resources(fragment)
            stages.append({"id": stage.id, 'content': stage_fragment.content})
            stage_stats[stage.id] = self._get_stage_completion_details(stage, target_workgroups, target_users)

        groups_data = self._build_groups_data(target_workgroups, stage_stats, filtered_users)
        visible_groups = [group for group in groups_data if group["group_visible"]]

        render_context = {
            'activity': self,
            'StageState': StageState,
            'stages': stages,
            'stages_count': len(stages),
            'groups': visible_groups,
            'filtered_out_workgroups': len(groups_data) - len(visible_groups),
            'stage_cell_width_percent': (100 - 30) / float(len(stages)),  # 30% is reserved for first column
            'assigned_to_groups_label': messages.ASSIGNED_TO_GROUPS_LABEL.format(group_count=len(groups_data))
        }
        fragment.add_content(self.render_template('dashboard_detail_view', render_context))

        return fragment

    def _render_user(self, user, stage_stats, filtered_students):
        """
        :param group_project_v2.project_api.dtos.ReducedUserDetail user:
        :param dict[str, StageCompletionDetailsData] stage_stats: Stage completion statistics
        :param set[int] filtered_students:  users filtered out from view
        :return: dict
        """

        return {
            'id': user.id, 'full_name': user.full_name, 'email': user.email,
            'is_filtered_out': user.id in filtered_students,
            'stage_states': {
                stage_id: stage_data.user_stats.get(user.id, StageState.UNKNOWN)
                for stage_id, stage_data in stage_stats.items()
            },
            'groups_to_grade': {
                stage_id: [
                    {'id': group.id, 'ta_grade_link': self.get_ta_review_link(group.id, stage_id)}
                    for group in stage_data.groups_to_grade.get(user.id, [])
                ]
                for stage_id, stage_data in stage_stats.items()
            }
        }

    def _render_workgroup(self, workgroup, stage_stats, filtered_students):
        """
        :param group_project_v2.project_api.dtos.WorkgroupDetails workgroup:
        :param dict[str, StageCompletionDetailsData] stage_stats: Stage completion statistics
        :param set[int] filtered_students:  users filtered out from view
        :return: dict
        """

        users = [
            self._render_user(user, stage_stats, filtered_students)
            for user in workgroup.users
        ]

        users.sort(key=itemgetter('is_filtered_out'))

        group_visible = any((not user['is_filtered_out'] for user in users))

        return {
            'id': workgroup.id,
            'ta_grade_link': self.get_ta_review_link(workgroup.id),
            'group_visible': group_visible,
            'stage_states': {
                stage_id: {
                    'internal_status': stage_data.internal_group_status.get(workgroup.id, StageState.UNKNOWN),
                    'external_status': stage_data.external_group_status.get(workgroup.id, StageState.NOT_AVAILABLE),
                    'external_status_label': stage_data.external_group_status_label.get(workgroup.id, ""),
                }
                for stage_id, stage_data in stage_stats.items()
            },
            'users': users
        }

    def _build_groups_data(self, workgroups, stage_stats, filtered_users):
        """
        Converts WorkgroupDetails into dict expected by dashboard_detail_view template.

        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] workgroups: Workgroups
        :param dict[str, StageCompletionDetailsData] stage_stats: Stage statistics - group-wise and user-wise completion
            data and groups_to_review.
        :param set[int] filtered_users: users filtered out from view - depending on actual view
            (dashboard or dashboard details) such students are either completely excluded, or included but diplayed
            differently
        :rtype: list[dict]
        :returns:
            List of dictionaries with the following format:
                * id - Group ID
                * stage_states - dictionary stage_id -> StateState
                * users - dictionary with the following format:
                    * id - User ID
                    * full_name - User full name
                    * email - user email
                    * stage_states - dictionary stage_id -> StageState
                    * groups_to_grade - dictionary stage_id -> list of groups to grade
        """
        return [
            self._render_workgroup(workgroup, stage_stats, filtered_users)
            for workgroup in workgroups
        ]

    @classmethod
    def _get_stage_completion_details(cls, stage, target_workgroups, target_students):
        """
        Gets stage completion stats from individual stage
        :param group_project_v2.stage.BaseGroupActivityStage stage: Get stage stats from this stage
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_students:
        :rtype: StageCompletionDetailsData
        :returns: Stage completion stats
        """
        completed_users, partially_completed_users = stage.get_users_completion(target_workgroups, target_students)
        user_stats = {}
        groups_to_grade = {}
        for user in target_students:
            state = StageState.NOT_STARTED
            if user.id in completed_users:
                state = StageState.COMPLETED
            elif user.id in partially_completed_users:
                state = StageState.INCOMPLETE
            user_stats[user.id] = state

            if isinstance(stage, PeerReviewStage):
                groups_to_grade[user.id] = stage.get_review_subjects(user.id)

        external_group_status, external_group_status_label, internal_group_status = cls._get_group_statuses(
            stage, target_workgroups, user_stats
        )

        return StageCompletionDetailsData(
            internal_group_status=internal_group_status,
            external_group_status=external_group_status,
            external_group_status_label=external_group_status_label,
            user_stats=user_stats,
            groups_to_grade=groups_to_grade
        )

    @classmethod
    def _get_group_statuses(cls, stage, target_workgroups, user_stats):
        internal_group_status, external_group_status, external_group_status_label = {}, {}, {}
        for group in target_workgroups:
            user_completions = [user_stats.get(user.id, StageState.UNKNOWN) for user in group.users]
            student_review_state = StageState.NOT_STARTED
            if all(completion == StageState.COMPLETED for completion in user_completions):
                student_review_state = StageState.COMPLETED
            elif any(completion != StageState.NOT_STARTED for completion in user_completions):
                student_review_state = StageState.INCOMPLETE
            elif any(completion == StageState.UNKNOWN for completion in user_completions):
                student_review_state = StageState.UNKNOWN
            internal_group_status[group.id] = student_review_state

            external_status = stage.get_external_group_status(group)
            external_group_status[group.id] = external_status
            external_group_status_label[group.id] = stage.get_external_status_label(external_status)
        return external_group_status, external_group_status_label, internal_group_status

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
        if grade_value is not None:
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
        grade_display_stage = self.get_grade_display_stage()
        if notifications_service and grade_display_stage:
            grade_display_stage.fire_grades_posted_notification(group_id, notifications_service)

    def calculate_grade(self, group_id):
        # pylint:disable=too-many-locals,too-many-branches,consider-using-set-comprehension
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
                # pylint: disable=no-else-return
                if user_value is None:
                    # if any are incomplete, we consider the whole set to be unusable
                    return None
                else:
                    user_grades.append(user_value)

            return user_grades

        admin_provided_grades = None
        if admin_reviewer_ids:
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
        if group_reviewer_ids:
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
        group_grade = round(mean(reviewer_grades)) if reviewer_grades else None

        return group_grade

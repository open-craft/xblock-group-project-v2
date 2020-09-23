from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import str
from past.utils import old_div
import logging
from collections import OrderedDict
from urllib.parse import urlencode  # pylint: disable=F0401
from datetime import datetime, timedelta
from lazy.lazy import lazy
import pytz
from xblock.core import XBlock
from xblock.fields import DateTime, Scope, Boolean
from web_fragments.fragment import Fragment
from xblockutils.studio_editable import XBlockWithPreviewMixin

from group_project_v2 import messages
from group_project_v2.api_error import ApiError
from group_project_v2.mixins import (
    CommonMixinCollection, XBlockWithUrlNameDisplayMixin, AdminAccessControlXBlockMixin,
    DashboardXBlockMixin, AuthXBlockMixin
)
from group_project_v2.notifications import StageNotificationsMixin
from group_project_v2.stage_components import (
    GroupProjectResourceXBlock, GroupProjectVideoResourceXBlock, ProjectTeamXBlock
)
from group_project_v2.utils import (
    gettext as _, HtmlXBlockShim, format_date, Constants, loader,
    groupwork_protected_view, add_resource, MUST_BE_OVERRIDDEN, get_link_to_block, get_block_content_id,
)
from group_project_v2.stage.utils import StageState


log = logging.getLogger(__name__)

STAGE_STATS_LOG_TPL = (
    "Calculating stage stats for stage %(stage)s "
    "all - %(target_users)s, completed - %(completed)s, partially completed - %(partially_completed)s"
)


@XBlock.wants("settings")
class BaseGroupActivityStage(
        CommonMixinCollection, DashboardXBlockMixin, XBlockWithPreviewMixin, StageNotificationsMixin,
        XBlockWithUrlNameDisplayMixin, AdminAccessControlXBlockMixin,
        XBlock,
):
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
        default=True
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
    EXTERNAL_STATUSES_LABEL_MAPPING = {}
    DEFAULT_EXTERNAL_STATUS_LABEL = ""

    js_file = None
    js_init = None

    template_location = 'stages'

    @property
    def id(self):
        return self.scope_ids.usage_id

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        """
        This property outputs an ordered dictionary of allowed nested XBlocks in form of block_category: block_caption.
        """
        blocks = [HtmlXBlockShim, GroupProjectResourceXBlock]
        if GroupProjectVideoResourceXBlock.is_available():
            blocks.append(GroupProjectVideoResourceXBlock)
        blocks.append(ProjectTeamXBlock)
        return blocks

    @lazy
    def activity(self):
        """
        :rtype: group_project_v2.group_project.GroupActivityXBlock
        """
        return self.get_parent()

    @property
    def allow_admin_grader_access(self):
        return False

    @property
    def content_id(self):
        return get_block_content_id(self)

    @property
    def activity_content_id(self):
        return self.activity.content_id

    @property
    def resources(self):
        return self.get_children_by_category(
            GroupProjectResourceXBlock.CATEGORY, GroupProjectVideoResourceXBlock.CATEGORY
        )

    @property
    def team_members(self):
        """
        Returns teammates to review. May throw `class`: OutsiderDisallowedError
        """
        if not self.is_group_member:
            return []

        try:
            result = []
            for team_member in self.workgroup.users:
                team_member_id = team_member.id
                if self.user_id == int(team_member_id):
                    continue
                result.append(self.project_api.get_member_data(team_member_id))
            return result
        except ApiError:
            return []

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

        if self.close_date is None:
            return False

        # A stage is closed at the end of the closing day.

        return self.close_date + timedelta(days=1) <= datetime.utcnow().replace(tzinfo=pytz.UTC)

    @property
    def completed(self):
        return self.get_stage_state() == StageState.COMPLETED

    @property
    def available_now(self):
        return self.is_open and not self.is_closed

    @property
    def url_name_caption(self):
        return messages.STAGE_URL_NAME_TEMPLATE.format(stage_name=self.STUDIO_LABEL)

    @property
    def can_mark_complete(self):
        return self.available_now and self.is_group_member

    @property
    def is_graded_stage(self):  # pylint: disable=no-self-use
        """
        If a stage is graded it is shown as graded on the the main dashboard, this property also is used by default
        implementation of ``shown_on_detail_view``.

        :rtype: bool
        """
        return False

    @property
    def shown_on_detail_view(self):
        """
        If true details of this stage are shown on the dashboard detail view, by default it returns ``is_graded_stage``.

        :rtype: bool
        """
        return self.is_graded_stage

    @property
    def dashboard_details_view_url(self):
        return self.activity.dashboard_details_url()

    def is_current_stage(self, context):
        target_stage_id = context.get(Constants.CURRENT_STAGE_ID_PARAMETER_NAME, None)
        if not target_stage_id:
            return False
        return target_stage_id == self.id

    def _view_render(self, context, view='student_view'):
        stage_fragment = self.get_stage_content_fragment(context, view)

        fragment = Fragment()
        fragment.add_fragment_resources(stage_fragment)
        render_context = {
            'stage': self, 'stage_content': stage_fragment.content,
            "ta_graded": self.activity.group_reviews_required_count
        }
        fragment.add_content(loader.render_template(self.STAGE_WRAPPER_TEMPLATE, render_context))
        if stage_fragment.js_init_fn:
            fragment.initialize_js(stage_fragment.js_init_fn)

        return fragment

    @groupwork_protected_view
    def student_view(self, context):
        return self._view_render(context)

    @groupwork_protected_view
    def author_preview_view(self, context):
        # if we use student_view or author_view Studio will wrap it in HTML that we don't want in the preview
        fragment = self._view_render(context, "preview_view")
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_fragment_resources(url_name_fragment)
        return fragment

    @groupwork_protected_view
    def author_edit_view(self, context):
        fragment = super(BaseGroupActivityStage, self).author_edit_view(context)
        url_name_fragment = self.get_url_name_fragment(self.url_name_caption)
        fragment.add_content(url_name_fragment.content)
        fragment.add_fragment_resources(url_name_fragment)
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
            fragment.add_fragment_resources(frag)

        render_context.update(context)
        fragment.add_content(loader.render_template(self.STAGE_CONTENT_TEMPLATE, render_context))

        if self.js_file:
            add_resource(self, 'javascript', self.js_file, fragment)

        if self.js_init:
            fragment.initialize_js(self.js_init)

        return fragment

    def mark_complete(self, user_id=None):
        user_id = user_id if user_id is not None else self.user_id
        self.runtime.publish(self, 'progress', {'user_id': user_id})

    def get_stage_state(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def get_dashboard_stage_state(self, target_workgroups, target_students):
        """
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_students:
        :return (str, dict[str, float]): Stage state and detailed stage stats as returned by `get_stage_stats`
        """
        state_stats = self.get_stage_stats(target_workgroups, target_students)
        if state_stats.get(StageState.COMPLETED, 0) == 1:
            stage_state = StageState.COMPLETED
        elif state_stats.get(StageState.INCOMPLETE, 0) > 0 or state_stats.get(StageState.COMPLETED, 0) > 0:
            stage_state = StageState.INCOMPLETE
        else:
            stage_state = StageState.NOT_STARTED

        return stage_state, state_stats

    def get_stage_stats(self, target_workgroups, target_students):  # pylint: disable=no-self-use
        """
        Calculates stage state stats for given workgroups and students
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_students:
        :return dict[str, float]:
            Percentage of students completed, partially completed and not started the stage as floats in range[0..1]
        """
        target_user_ids = set(user.id for user in target_students)
        if not target_user_ids:
            return {
                StageState.COMPLETED: None,
                StageState.INCOMPLETE: None,
                StageState.NOT_STARTED: None
            }

        target_user_count = float(len(target_user_ids))

        completed_users_ids, partially_completed_users_ids = self.get_users_completion(
            target_workgroups, target_students
        )
        log_format_data = dict(
            stage=self.display_name, target_users=target_user_ids, completed=completed_users_ids,
            partially_completed=partially_completed_users_ids
        )
        log.info(STAGE_STATS_LOG_TPL, log_format_data)

        completed_ratio = old_div(len(completed_users_ids & target_user_ids), target_user_count)
        partially_completed_ratio = old_div(len(partially_completed_users_ids & target_user_ids), target_user_count)

        return {
            StageState.COMPLETED: completed_ratio,
            StageState.INCOMPLETE: partially_completed_ratio,
            StageState.NOT_STARTED: 1 - completed_ratio - partially_completed_ratio
        }

    def get_users_completion(self, target_workgroups, target_users):
        """
        Returns sets of completed user ids and partially completed user ids
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_users:
        :rtype: (set[int], set[int])
        """
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

    def get_external_group_status(self, group):  # pylint: disable=unused-argument, no-self-use
        """
        Calculates external group status for the Stage.
        Meaning of external status varies by Stage - see actual implementations docstrings.
        :param group_project_v2.project_api.dtos.WorkgroupDetails group: workgroup
        :rtype: StageState
        """
        return StageState.NOT_AVAILABLE

    def get_external_status_label(self, status):
        """
        Gets human-friendly label for external status.
        Label vary by stage, so consult with actual implementaiton for details
        :param StageState status: external stage status
        :rtype: str
        """
        return self.EXTERNAL_STATUSES_LABEL_MAPPING.get(status, self.DEFAULT_EXTERNAL_STATUS_LABEL)

    def navigation_view(self, context):
        """
        Renders stage content for navigation view
        :param dict context:
        :rtype: Fragment
        """
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

    @classmethod
    def make_human_stats(cls, stats):
        """
        Readies stats dictionary for presentation, by sorting it's contents, and converting
        ratios to percentages.
        """
        return OrderedDict([
            (
                StageState.get_human_name(stage),
                stats[stage] * 100 if stats[stage] is not None else None
            )
            for stage in (StageState.NOT_STARTED, StageState.INCOMPLETE, StageState.COMPLETED)
        ])

    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_view(self, context):
        """
        Renders stage content for dashboard view.
        :param dict context:
        :rtype: Fragment
        """
        fragment = Fragment()

        target_workgroups = context.get(Constants.TARGET_WORKGROUPS)
        target_students = context.get(Constants.TARGET_STUDENTS)
        filtered_students = context.get(Constants.FILTERED_STUDENTS)

        students_to_display = [student for student in target_students if student.id not in filtered_students]

        state, stats = self.get_dashboard_stage_state(target_workgroups, students_to_display)
        human_stats = self.make_human_stats(stats)
        render_context = {
            'stage': self, 'stats': human_stats, 'stage_state': state, 'ta_graded': self.activity.is_ta_graded
        }
        render_context.update(context)
        fragment.add_content(self.render_template('dashboard_view', render_context))
        return fragment

    @AuthXBlockMixin.check_dashboard_access_for_current_user
    def dashboard_detail_view(self, context):
        """
        Renders stage header for dashboard details view.
        :param dict context:
        :rtype: Fragment
        """
        fragment = Fragment()
        render_context = {
            'stage': self, 'ta_graded': self.activity.is_ta_graded,
            'download_incomplete_emails_handler_url': self.get_incomplete_emails_handler_url()
        }
        fragment.add_content(self.render_template('dashboard_detail_view', render_context))
        return fragment

    def get_incomplete_emails_handler_url(self):
        base_url = self.runtime.handler_url(self.activity.project, 'download_incomplete_list')
        query_params = {
            Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: self.id
        }
        return base_url + '?' + urlencode(query_params)

    def get_new_stage_state_data(self):
        return {
            "activity_id": str(self.activity.id),
            "stage_id": str(self.id),
            "state": self.get_stage_state()
        }

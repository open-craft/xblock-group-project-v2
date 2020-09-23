from builtins import str
import logging
from xblock.core import XBlock
from xblock.fields import String, Scope
from xblock.validation import ValidationMessage
from web_fragments.fragment import Fragment


from group_project_v2 import messages
from group_project_v2.api_error import ApiError
from group_project_v2.stage.base import BaseGroupActivityStage
from group_project_v2.stage.mixins import SimpleCompletionStageMixin
from group_project_v2.stage_components import SubmissionsStaticContentXBlock, GroupProjectSubmissionXBlock
from group_project_v2.utils import gettext as _, groupwork_protected_handler, loader
from group_project_v2.stage.utils import StageState, DISPLAY_NAME_NAME, DISPLAY_NAME_HELP

log = logging.getLogger(__name__)


class BasicStage(SimpleCompletionStageMixin, BaseGroupActivityStage):

    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Text Stage")
    )

    CATEGORY = 'gp-v2-stage-basic'

    NAVIGATION_LABEL = _(u'Overview')
    STUDIO_LABEL = _(u"Text")

    def student_view(self, context):
        fragment = super(BasicStage, self).student_view(context)

        if self.can_mark_complete:
            self.mark_complete()

        return fragment


class CompletionStage(SimpleCompletionStageMixin, BaseGroupActivityStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Completion Stage")
    )

    CATEGORY = 'gp-v2-stage-completion'
    STAGE_CONTENT_TEMPLATE = "templates/html/stages/completion.html"

    NAVIGATION_LABEL = _(u'Task')
    STUDIO_LABEL = _(u"Completion")

    js_file = "public/js/stages/completion.js"
    js_init = "GroupProjectCompletionStage"

    STAGE_ACTION = _(u"mark stage as complete")

    @XBlock.json_handler
    @groupwork_protected_handler
    def stage_completed(self, _data, _suffix=''):
        if not self.available_now:
            template = messages.STAGE_NOT_OPEN_TEMPLATE if not self.is_open else messages.STAGE_CLOSED_TEMPLATE
            return {'result': 'error', 'msg': template.format(action=self.STAGE_ACTION)}

        try:
            if self.can_mark_complete:
                self.mark_complete()
            return {
                'result': 'success',
                'msg': messages.STAGE_COMPLETION_MESSAGE,
                'new_stage_states': [self.get_new_stage_state_data()]
            }
        except ApiError as exception:
            log.exception(exception.message)
            return {'result': 'error', 'msg': exception.message}

    def mark_complete(self, user_id=None):
        user_id = user_id or self.user_id
        if str(user_id) != str(self.user_id):
            raise Exception("Can only mark as complete for current user")
        return super(CompletionStage, self).mark_complete(user_id)

    def get_stage_content_fragment(self, context, view='student_view'):
        extra_context = {
            'completed': self.completed
        }
        extra_context.update(context)
        return super(CompletionStage, self).get_stage_content_fragment(extra_context, view)


class SubmissionStage(BaseGroupActivityStage):
    display_name = String(
        display_name=DISPLAY_NAME_NAME,
        help=DISPLAY_NAME_HELP,
        scope=Scope.content,
        default=_(u"Submission Stage")
    )

    CATEGORY = 'gp-v2-stage-submission'

    NAVIGATION_LABEL = _(u'Task')
    STUDIO_LABEL = _(u"Deliverable")

    EXTERNAL_STATUSES_LABEL_MAPPING = {
        StageState.NOT_STARTED: _("Pending Upload"),
        StageState.INCOMPLETE: _("Pending Upload"),
        StageState.COMPLETED: _("Uploaded"),
    }
    DEFAULT_EXTERNAL_STATUS_LABEL = _("Unknown")

    submissions_stage = True

    STAGE_ACTION = _(u"upload submission")

    @property
    def allowed_nested_blocks(self):
        blocks = super(SubmissionStage, self).allowed_nested_blocks
        blocks.extend([SubmissionsStaticContentXBlock, GroupProjectSubmissionXBlock])
        return blocks

    @property
    def is_graded_stage(self):
        return False

    @property
    def shown_on_detail_view(self):  # pylint: disable=no-self-use
        return True

    @property
    def submissions(self):
        """
        :rtype: collections.Iterable[GroupProjectSubmissionXBlock]
        """
        return self.get_children_by_category(GroupProjectSubmissionXBlock.CATEGORY)

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
                messages.SUBMISSIONS_BLOCKS_ARE_MISSING.format(
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
            for user in self.workgroup.users:
                self.mark_complete(user.id)

    def get_stage_state(self):
        # pylint: disable=no-else-return
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
            fragment.add_fragment_resources(submission_fragment)
            submission_contents.append(submission_fragment.content)

        context = {'stage': self, 'submission_contents': submission_contents}
        fragment.add_content(loader.render_template(template, context))

        return fragment

    def review_submissions_view(self, context):
        # transparently passing group_id via context
        return self._render_view(
            'submission_review_view', "templates/html/stages/submissions_review_view.html", context
        )

    def get_users_completion(self, target_workgroups, target_users):
        """
        Returns sets of completed user ids and partially completed user ids
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_users:
        :rtype: (set[int], set[int])
        """
        completed_users = []
        partially_completed_users = []
        for group in target_workgroups:
            group_stage_state = self.get_external_group_status(group)
            workgroup_user_ids = [user.id for user in group.users]

            if group_stage_state == StageState.COMPLETED:
                completed_users.extend(workgroup_user_ids)
            if group_stage_state == StageState.INCOMPLETE:
                partially_completed_users.extend(workgroup_user_ids)

        return set(completed_users), set(partially_completed_users)  # removing duplicates - just in case

    def get_external_group_status(self, group):
        """
        Calculates external group status for the Stage.
        For Submissions stage, external status is the same as internal one: "have workgroup submitted all uploads?"
        :param group_project_v2.project_api.dtos.WorkgroupDetails group: workgroup
        :rtype: StageState
        """
        upload_ids = set(submission.upload_id for submission in self.submissions)
        group_submissions = self.project_api.get_latest_workgroup_submissions_by_id(group.id)
        uploaded_submissions = set(group_submissions.keys())

        has_all = uploaded_submissions >= upload_ids
        has_some = bool(uploaded_submissions & upload_ids)
        # pylint: disable=no-else-return
        if has_all:
            return StageState.COMPLETED
        elif has_some:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

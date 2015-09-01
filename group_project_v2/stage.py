from datetime import datetime
import json
import logging
import itertools

from lazy.lazy import lazy
import pytz
import webob
from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime, Boolean
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin, XBlockWithPreviewMixin

from group_project_v2.api_error import ApiError
from group_project_v2.mixins import (
    ChildrenNavigationXBlockMixin,
    WorkgroupAwareXBlockMixin, XBlockWithComponentsMixin,
    XBlockWithUrlNameDisplayMixin, AdminAccessControlXBlockMixin
)
from group_project_v2.notifications import StageNotificationsMixin
from group_project_v2.stage_components import (
    ProjectTeamXBlock, GroupProjectResourceXBlock, GroupProjectVideoResourceXBlock,
    GroupProjectSubmissionXBlock, SubmissionsStaticContentXBlock,
    PeerSelectorXBlock, GroupSelectorXBlock, GroupProjectReviewQuestionXBlock, GradeRubricStaticContentXBlock,
    GroupProjectTeamEvaluationDisplayXBlock, GroupProjectGradeEvaluationDisplayXBlock,
)
from group_project_v2.utils import (
    loader, format_date, gettext as _, make_key, get_link_to_block, HtmlXBlockProxy, Constants, MUST_BE_OVERRIDDEN,
    outsider_disallowed_protected_view, outsider_disallowed_protected_handler, key_error_protected_handler,
    conversion_protected_handler,
    add_resource)

log = logging.getLogger(__name__)


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


class ReviewState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


DISPLAY_NAME_NAME = _(u"Display Name")
DISPLAY_NAME_HELP = _(U"This is a name of the stage")


class SimpleCompletionStageMixin(object):
    """
    runtime.publish(block, 'progress', {'user_id': user_id}) properly creates completion records, but they are
    unavailable to API until current request is ended. They are created in transaction and looks like in LMS every
    request have dedicated transaction, but that's speculation. Anyway, we can't rely on
    runtime.publish - project_api.get_stage_id to update stage state and get new state in single run.
    """
    completed = Boolean(
        display_name=_(u"Completed"),
        scope=Scope.user_state
    )

    def get_stage_state(self):
        if self.completed:
            return StageState.COMPLETED
        return StageState.NOT_STARTED

    def mark_complete(self, user_id=None):
        result = super(SimpleCompletionStageMixin, self).mark_complete(user_id)
        self.completed = True
        return result


class BaseGroupActivityStage(
    XBlockWithPreviewMixin, XBlockWithComponentsMixin, StageNotificationsMixin,
    XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin,
    ChildrenNavigationXBlockMixin, XBlockWithUrlNameDisplayMixin,
    WorkgroupAwareXBlockMixin, AdminAccessControlXBlockMixin
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
    STAGE_COMPLETION_MESSAGE = _(u"This task has been marked as complete.")

    js_file = None
    js_init = None

    STAGE_NOT_OPEN_TEMPLATE = _(u"Can't {action} as it's not yet opened.")
    STAGE_CLOSED_TEMPLATE = _(u"Can't {action} as it's closed.")
    STAGE_URL_NAME_TEMPLATE = _(u"url_name to link to this {stage_name}:")

    @property
    def id(self):
        return self.scope_ids.usage_id

    @property
    def allowed_nested_blocks(self):  # pylint: disable=no-self-use
        """
        This property outputs an ordered dictionary of allowed nested XBlocks in form of block_category: block_caption.
        """
        blocks = [HtmlXBlockProxy, GroupProjectResourceXBlock]
        if GroupProjectVideoResourceXBlock.is_available():
            blocks.append(GroupProjectVideoResourceXBlock)
        blocks.append(ProjectTeamXBlock)
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
            for team_member in self.workgroup["users"]:
                team_member_id = team_member["id"]
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

    @property
    def can_mark_complete(self):
        return self.available_now and self.is_group_member

    def is_current_stage(self, context):
        target_stage_id = context.get(Constants.CURRENT_STAGE_ID_PARAMETER_NAME, None)
        if not target_stage_id:
            return False
        return target_stage_id == self.id

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
            add_resource(self, 'javascript', self.js_file, fragment)

        if self.js_init:
            fragment.initialize_js(self.js_init)

        return fragment

    def mark_complete(self, user_id=None):
        user_id = user_id if user_id is not None else self.user_id
        self.runtime.publish(self, 'progress', {'user_id': user_id})

    def get_stage_state(self):
        raise NotImplementedError(MUST_BE_OVERRIDDEN)

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

    def get_new_stage_state_data(self):
        return {
            "activity_id": str(self.activity.id),
            "stage_id": str(self.id),
            "state": self.get_stage_state()
        }


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
    @outsider_disallowed_protected_handler
    def stage_completed(self, data, suffix=''):  # pylint: disable=unused-argument
        if not self.available_now:
            template = self.STAGE_NOT_OPEN_MESSAGE if not self.is_open else self.STAGE_CLOSED_MESSAGE
            return {'result': 'error',  'msg': template.format(action=self.STAGE_ACTION)}

        try:
            if self.can_mark_complete:
                self.mark_complete()
            return {
                'result': 'success',
                'msg': self.STAGE_COMPLETION_MESSAGE,
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

    submissions_stage = True

    STAGE_ACTION = _(u"upload submission")

    @property
    def allowed_nested_blocks(self):
        blocks = super(SubmissionStage, self).allowed_nested_blocks
        blocks.extend([SubmissionsStaticContentXBlock, GroupProjectSubmissionXBlock])
        return blocks

    @property
    def submissions(self):
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
        pass


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


STAGE_TYPES = (
    BasicStage.CATEGORY,
    CompletionStage.CATEGORY,
    SubmissionStage.CATEGORY,
    TeamEvaluationStage.CATEGORY,
    PeerReviewStage.CATEGORY,
    EvaluationDisplayStage.CATEGORY,
    GradeDisplayStage.CATEGORY
)

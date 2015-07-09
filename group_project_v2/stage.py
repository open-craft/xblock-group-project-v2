from collections import OrderedDict
from datetime import datetime
from lazy.lazy import lazy
import pytz
from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime, Boolean
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin

from group_project_v2.components.review import GroupProjectReviewQuestionXBlock, GroupProjectReviewAssessmentXBlock
from group_project_v2.project_api import project_api
from group_project_v2.utils import loader, inner_html, format_date, gettext as _, ChildrenNavigationXBlockMixin


class StageType(object):
    NORMAL = 'normal'
    UPLOAD = 'upload'
    PEER_REVIEW = 'peer_review'
    PEER_ASSESSMENT = 'peer_assessment'
    GROUP_REVIEW = 'group_review'
    GROUP_ASSESSMENT = 'group_assessment'


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


class ResourceType(object):
    NORMAL = 'normal'
    OOYALA_VIDEO = 'ooyala'


class GroupProjectResourceXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-resource"

    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/project_navigator/resource_xblock_view.html'

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the resource"),
        scope=Scope.settings,
        default="Group Project V2 Resource"
    )

    description = String(
        display_name=_(u"Resource Description"),
        scope=Scope.settings
    )

    resource_location = String(
        display_name=_(u"Resource location"),
        help=_(u"A url to download/view the resource"),
        scope=Scope.settings,
    )

    grading_criteria = Boolean(
        display_name=_(u"Grading criteria?"),
        help=_(u"If true, resource will be treated as grading criteria"),
        scope=Scope.settings,
        default=False
    )

    editable_fields = ('display_name', 'description', 'resource_location', 'grading_criteria')

    def student_view(self, context):
        return Fragment()

    def resources_view(self, context):
        fragment = Fragment()
        render_context = {'resource': self}
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        return fragment


class GroupProjectSubmissionXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-submission"
    PROJECT_NAVIGATOR_VIEW_TEMPLATE = 'templates/html/project_navigator/submission_xblock_view.html'

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the submission"),
        scope=Scope.settings,
        default="Group Project V2 Submission"
    )

    description = String(
        display_name=_(u"Resource Description"),
        scope=Scope.settings
    )

    upload_id = String(
        display_name=_(u"Upload ID"),
        help=_(U"This string is used as an identifier for an upload. "
               U"Submissions sharing the same Upload ID will be updated simultaneously"),
    )

    editable_fields = ('display_name', 'description', 'upload_id')

    def student_view(self, context):
        return Fragment()

    def project_navigator_view(self, context):
        fragment = Fragment()
        render_context = {'submission': self, 'upload': None}  # FIXME: fetch upload data from project_api
        render_context.update(context)
        fragment.add_content(loader.render_template(self.PROJECT_NAVIGATOR_VIEW_TEMPLATE, render_context))
        return fragment


class BaseGroupActivityStage(XBlock, ChildrenNavigationXBlockMixin,
                             StudioEditableXBlockMixin, StudioContainerXBlockMixin):
    submissions_stage = False

    display_name = String(
        display_name=_(u"Display Name"),
        help=_(U"This is a name of the stage"),
        scope=Scope.settings,
        default="Group Project V2 Stage"
    )

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

    STAGE_WRAPPER_TEMPLATE = 'templates/html/stages/stage_wrapper.html'

    editable_fields = ('display_name', 'open_date', 'close_date')
    has_children = True
    has_score = False  # TODO: Group project V1 are graded at activity level. Check if we need to follow that

    COMMON_ALLOWED_BLOCKS = OrderedDict([
        ("html", _(u"HTML")),
        (GroupProjectResourceXBlock.CATEGORY, _(u"Resource"))
    ])
    STAGE_SPECIFIC_ALLOWED_BLOCKS = {}

    @property
    def id(self):
        return self.scope_ids.usage_id

    @lazy
    def allowed_nested_blocks(self):
        blocks = OrderedDict()
        blocks.update(self.COMMON_ALLOWED_BLOCKS)
        blocks.update(self.STAGE_SPECIFIC_ALLOWED_BLOCKS)
        return blocks

    @lazy
    def activity(self):
        return self.get_parent()

    @property
    def resources(self):
        return self._get_children_by_category(GroupProjectResourceXBlock.CATEGORY)

    @property
    def grading_criteria(self):
        return (resource for resource in self.resources if resource.grading_criteria)

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
        if self.activity.is_admin_grader:
            return False

        return (self.close_date is not None) and (self.close_date < datetime.utcnow().replace(tzinfo=pytz.UTC))

    def student_view(self, context):
        stage_fragment = self.get_stage_content_fragment(context)

        fragment = Fragment()
        fragment.add_frag_resources(stage_fragment)
        render_context = {
            'stage': self, 'stage_content': stage_fragment.content,
            "ta_graded": self.activity.group_reviews_required_count
        }
        fragment.add_content(loader.render_template(self.STAGE_WRAPPER_TEMPLATE, render_context))

        return fragment

    def get_stage_content_fragment(self, context):
        return self.get_children_fragment(context)

    def author_preview_view(self, context):
        return self.student_view(context)

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(
            loader.render_template('templates/html/add_buttons.html', {'child_blocks': self.allowed_nested_blocks})
        )
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        return fragment

    def get_stage_state(self):
        """
        Gets stage completion state
        """
        users_in_group, completed_users = project_api.get_stage_state(
            self.activity.course_id,
            self.activity.id,
            self.activity.user_id,
            self.id
        )

        if not users_in_group or not completed_users:
            return StageState.NOT_STARTED
        if users_in_group <= completed_users:
            return StageState.COMPLETED
        if users_in_group & completed_users:
            return StageState.INCOMPLETE
        else:
            return StageState.NOT_STARTED

    def navigation_view(self, context):
        fragment = Fragment()
        rendering_context = {
            'stage': self,
            'activity_id': self.activity.id,
            'stage_state': self.get_stage_state()
        }
        rendering_context.update(context)
        fragment.add_content(loader.render_template("templates/html/stages/navigation_view.html", rendering_context))
        return fragment

    def resources_view(self, context):
        fragment = Fragment()

        resource_contents = []
        for resource in self.resources:
            resource_fragment = resource.render('resources_view', context)
            fragment.add_frag_resources(resource_fragment)
            resource_contents.append(resource_fragment.content)

        context = {'activity': self, 'resource_contents': resource_contents}
        fragment.add_content(loader.render_template("templates/html/stages/resources_view.html", context))

        return fragment


class BasicStage(BaseGroupActivityStage):
    type = u'Text'
    CATEGORY = 'group-project-v2-stage-basic'


class SubmissionStage(BaseGroupActivityStage):
    type = u'Task'
    CATEGORY = 'group-project-v2-stage-submission'

    submissions_stage = True
    STAGE_SPECIFIC_ALLOWED_BLOCKS = OrderedDict([
        (GroupProjectSubmissionXBlock.CATEGORY, _(u"Submission"))
    ])

    @property
    def submissions(self):
        return self._get_children_by_category(GroupProjectSubmissionXBlock.CATEGORY)

    @property
    def is_upload_available(self):
        return self.submissions and self.is_open and not self.is_closed

    @property
    def has_submissions(self):
        return any([submission.lcaotion for submission in self.submissions])

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
    def has_all_submissions(self):
        uploaded_submissions = [s for s in self.submissions if hasattr(s, 'location') and s.location]
        return len(uploaded_submissions) == len(list(self.submissions))

    def project_navigator_submissions_view(self, context):
        fragment = Fragment()

        submisison_frargments = [sub.render('project_navigator_view', context) for sub in self.submissions]

        context = {
            'stage': self,
            'activity_id': self.activity.id,
            'submissions': [frag.content for frag in submisison_frargments]
        }
        fragment.add_content(loader.render_template(
            "templates/html/project_navigator/submission_stage_xblock_view.html",
            context
        ))

        for frag in submisison_frargments:
            fragment.add_frag_resources(frag)

        return fragment


class ReviewBaseStage(BaseGroupActivityStage):
    type = u'Grade'
    STAGE_SPECIFIC_ALLOWED_BLOCKS = {GroupProjectReviewQuestionXBlock.CATEGORY: _(u"Review Question")}

    @property
    def questions(self):
        return self._get_children_by_category(GroupProjectReviewQuestionXBlock.CATEGORY)

    @property
    def grade_questions(self):
        return (question for question in self._questions if question.grade)

    @property
    def grade_header_html(self):
        return inner_html(self._grade_header)

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


class PeerReviewStage(ReviewBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_review.html'
    CATEGORY = 'group-project-v2-stage-peer-review'


class GroupReviewStage(ReviewBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/group_review.html'
    CATEGORY = 'group-project-v2-stage-group-review'


class AssessmentBaseStage(BaseGroupActivityStage):
    type = u'Evaluation'
    HTML_TEMPLATE = 'templates/html/stages/peer_assessment.html'

    STAGE_SPECIFIC_ALLOWED_BLOCKS = OrderedDict([
        (GroupProjectReviewAssessmentXBlock.CATEGORY, _(u"Review Question"))
    ])

    @property
    def assessments(self):
        return self._get_children_by_category(GroupProjectReviewAssessmentXBlock.CATEGORY)

    def validate(self):
        violations = super(AssessmentBaseStage, self).validate()

        if not self.assessments:
            violations.add(ValidationMessage(
                ValidationMessage.ERROR,
                _(u"Assessments are not specified for {class_name} '{stage_title}'").format(
                    class_name=self.__class__.__name__, stage_title=self.display_name
                )
            ))

        return violations


class PeerAssessmentStage(AssessmentBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/peer_assessment.html'
    CATEGORY = 'group-project-v2-stage-peer-assessment'


class GroupAssessmentStage(AssessmentBaseStage):
    STAGE_CONTENT_TEMPLATE = 'templates/html/stages/group_assessment.html'
    CATEGORY = 'group-project-v2-stage-group-assessment'


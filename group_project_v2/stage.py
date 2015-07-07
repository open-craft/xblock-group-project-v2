from collections import OrderedDict
import copy
from datetime import date
from lazy.lazy import lazy
from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin

from group_project_v2.components.review import GroupActivityQuestion, GroupActivityAssessment, \
    GroupProjectReviewQuestionXBlock, GroupProjectReviewAssessmentXBlock
from group_project_v2.utils import loader, inner_html, format_date, gettext as _


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


class ImproperlyConfiguredActivityException(Exception):
    pass


class ResourceXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-resource"

    def student_view(self, context):
        return Fragment()
    # for document in doc_tree.findall("./resources/document"):
    #     doc_type = document.get("type", ResourceType.NORMAL)
    #     if doc_type not in (ResourceType.NORMAL, ResourceType.OOYALA_VIDEO):
    #         raise ImproperlyConfiguredActivityException("Unknown resource type %s" % doc_type)
    #     self._resources.append(DottableDict({
    #         "title": document.get("title"),
    #         "description": document.get("description"),
    #         "location": document.text,
    #         "type": doc_type,
    #         "grading_criteria": document.get("grading_criteria") == "true"
    #     }))

class SubmissionXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-submission"

    def student_view(self, context):
        return Fragment()
    # for document in doc_tree.findall("./submissions/document"):
    #     self._submissions.append(DottableDict({
    #         "id": document.get("id"),
    #         "title": document.get("title"),
    #         "description": document.get("description"),
    #     }))


class BaseGroupActivityStage(XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin):
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

    HTML_TEMPLATE = 'templates/html/stages/text.html'

    editable_fields = ('display_name', 'open_date', 'close_date')
    has_children = True
    has_score = False  # TODO: Group project V1 are graded at activity level. Check if we need to follow that

    COMMON_ALLOWED_BLOCKS = OrderedDict([
        ("html", _(u"HTML")),
        (ResourceXBlock.CATEGORY, _(u"Resource"))
    ])
    STAGE_SPECIFIC_ALLOWED_BLOCKS = {}

    @lazy
    def allowed_nested_blocks(self):
        blocks = OrderedDict()
        blocks.update(self.COMMON_ALLOWED_BLOCKS)
        blocks.update(self.STAGE_SPECIFIC_ALLOWED_BLOCKS)
        return blocks

    @lazy
    def activity(self):
        return self.get_parent()

    @lazy
    def _children(self):
        return [self.runtime.get_block(child_id) for child_id in self.children]

    def _get_children_by_category(self, child_category):
        return [child for child in self.children if child.category == child_category]

    @property
    def resources(self):
        return self._get_children_by_category(ResourceXBlock.CATEGORY)

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
        return (self.open_date is None) or (self.open_date <= date.today())

    @property
    def is_closed(self):
        # If this stage is being loaded for the purposes of a TA grading,
        # then we never close the stage - in this way a TA can impose any
        # action necessary even if it has been closed to the group members
        if self.activity.is_admin_grader:
            return False

        return (self.close_date is not None) and (self.close_date < date.today())

    def student_view(self, context):
        fragment = Fragment()
        children_content = []
        for child in self._children:
            child_fragment = child.render('student_view', context)
            fragment.add_frag_resources(child_fragment)
            children_content.append(child_fragment.content)

        render_context = {"activity_stage": self, 'children_content': children_content}
        return loader.render_template(self.HTML_TEMPLATE, render_context)

    def author_preview_view(self, context):
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        return fragment

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


class BasicStage(BaseGroupActivityStage):
    HTML_TEMPLATE = 'templates/html/stages/text.html'
    type = u'Text'
    CATEGORY = 'group-project-v2-stage-basic'


class SubmissionStage(BaseGroupActivityStage):
    HTML_TEMPLATE = 'templates/html/stages/upload.html'
    type = u'Task'
    CATEGORY = 'group-project-v2-stage-submission'

    submissions_stage = True
    STAGE_SPECIFIC_ALLOWED_BLOCKS = OrderedDict([
        (SubmissionXBlock.CATEGORY, _(u"Submission"))
    ])

    @property
    def submissions(self):
        return self._get_children_by_category(SubmissionXBlock.CATEGORY)

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
    HTML_TEMPLATE = 'templates/html/stages/peer_review.html'
    CATEGORY = 'group-project-v2-stage-peer-review'


class GroupReviewStage(ReviewBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/group_review.html'
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
    HTML_TEMPLATE = 'templates/html/stages/peer_assessment.html'
    CATEGORY = 'group-project-v2-stage-peer-assessment'


class GroupAssessmentStage(AssessmentBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/group_assessment.html'
    CATEGORY = 'group-project-v2-stage-group-assessment'


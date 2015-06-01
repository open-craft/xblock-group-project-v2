import copy
import abc
from datetime import date

from group_project_v2.components.review import GroupActivityQuestion, GroupActivityAssessment
from group_project_v2.utils import DottableDict, render_template, parse_date, inner_html, outer_html, format_date


class StageType(object):
    NORMAL = 'normal'
    UPLOAD = 'upload'
    PEER_REVIEW = 'peer_review'
    PEER_ASSESSMENT = 'peer_assessment'
    GROUP_REVIEW = 'group_review'
    GROUP_ASSESSMENT = 'group_assessment'


class BaseGroupActivityStage(object):
    __metaclass__ = abc.ABCMeta

    XML_TEMPLATE = 'templates/xml/activity_stage.xml'
    HTML_TEMPLATE = 'templates/html/stages/text.html'

    def __init__(self, doc_tree, grading_override):
        self.grading_override = grading_override
        self._resources = []

        self.open_date = None
        self.close_date = None

        self.id = doc_tree.get("id")
        self.title = doc_tree.get("title")
        self._content = doc_tree.find("./content")

        if doc_tree.get("open"):
            self.open_date = parse_date(doc_tree.get("open"))

        if doc_tree.get("close"):
            self.close_date = parse_date(doc_tree.get("close"))

        # import resources
        for document in doc_tree.findall("./resources/document"):
            self._resources.append(DottableDict({
                "title": document.get("title"),
                "description": document.get("description"),
                "location": document.text,
                "grading_criteria": document.get("grading_criteria") == "true"
            }))

    @property
    def name(self):
        """
        Alias of title
        """
        return self.title

    @property
    def content_html(self):
        return inner_html(self._content)

    @property
    def resources(self):
        return tuple(self._resources)

    @property
    def grading_criteria(self):
        return (resource for resource in self._resources if resource.grading_criteria)

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
        if self.grading_override:
            return False

        return (self.close_date is not None) and (self.close_date < date.today())

    def _render(self, template):
        return render_template(template, {"activity_stage": self})

    @property
    def export_xml(self):
        return self._render(self.XML_TEMPLATE)

    @property
    def render(self):
        return self._render(self.HTML_TEMPLATE)


class BasicStage(BaseGroupActivityStage):
    HTML_TEMPLATE = 'templates/html/stages/text.html'


class SubmissionStage(BaseGroupActivityStage):
    HTML_TEMPLATE = 'templates/html/stages/upload.html'

    def __init__(self, doc_tree, grading_override):
        super(SubmissionStage, self).__init__(doc_tree, grading_override)
        self._submissions = []
        self._upload = doc_tree.find("./upload")

        # import submission definitions
        for document in doc_tree.findall("./submissions/document"):
            self._submissions.append(DottableDict({
                "id": document.get("id"),
                "title": document.get("title"),
                "description": document.get("description"),
            }))

    @property
    def submissions(self):
        # need to be a list to support "if activity_stage.resources" check in templates
        return self._submissions

    @property
    def upload_html(self):
        return inner_html(self._upload)

    @property
    def is_upload_available(self):
        return self.submissions and self.is_open and not self.is_closed

    @property
    def has_submissions(self):
        return any([getattr(submission, 'location', None) for submission in self.submissions])


class ReviewBaseStage(BaseGroupActivityStage):
    __metaclass__ = abc.ABCMeta

    def __init__(self, doc_tree, grading_override):
        super(ReviewBaseStage, self).__init__(doc_tree, grading_override)
        self._questions = []

        self._grade_header = doc_tree.find("./grade_header")

        # import any questions
        for question in doc_tree.findall("./question"):
            question = GroupActivityQuestion(question, self)
            self._questions.append(question)

    @property
    def questions(self):
        return tuple(self._questions)

    @property
    def grade_questions(self):
        return (question for question in self._questions if question.grade)

    @property
    def grade_header_html(self):
        return inner_html(self._grade_header)


class PeerReviewStage(ReviewBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/peer_review.html'


class GroupReviewStage(ReviewBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/group_review.html'


class AssessmentBaseStage(BaseGroupActivityStage):
    __metaclass__ = abc.ABCMeta

    HTML_TEMPLATE = 'templates/html/stages/peer_assessment.html'

    def __init__(self, doc_tree, grading_override):
        super(AssessmentBaseStage, self).__init__(doc_tree, grading_override)
        self._assessments = []

        # import any assessments
        for assessment in doc_tree.findall("./assessment"):
            self._assessments.append(GroupActivityAssessment(assessment))

    @property
    def assessments(self):
        return tuple(self._assessments)


class PeerAssessmentStage(AssessmentBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/peer_assessment.html'


class GroupAssessmentStage(AssessmentBaseStage):
    HTML_TEMPLATE = 'templates/html/stages/group_assessment.html'


class GroupActivityStageFactory(object):
    _type_map = {}

    _default_stage_class = BasicStage

    @classmethod
    def register(cls, type, stage_class):
        cls._type_map[type] = stage_class

    @classmethod
    def create(cls, xml_node, grading_override):
        stage_type = xml_node.get("type")
        stage_class = cls._type_map.get(stage_type, cls._default_stage_class)

        return stage_class(xml_node, grading_override)

GroupActivityStageFactory.register(StageType.NORMAL, BasicStage)
GroupActivityStageFactory.register(StageType.UPLOAD, SubmissionStage)
GroupActivityStageFactory.register(StageType.PEER_REVIEW, PeerReviewStage)
GroupActivityStageFactory.register(StageType.GROUP_REVIEW, GroupReviewStage)
GroupActivityStageFactory.register(StageType.PEER_ASSESSMENT, PeerAssessmentStage)
GroupActivityStageFactory.register(StageType.GROUP_ASSESSMENT, GroupAssessmentStage)

import copy
from datetime import date

from group_project_v2.components.review import GroupActivityQuestion, GroupActivityAssessment
from group_project_v2.utils import DottableDict, render_template, parse_date, inner_html, outer_html


STAGE_TYPES = DottableDict(
    NORMAL='normal',
    UPLOAD='upload',
    PEER_REVIEW='peer_review',
    PEER_ASSESSMENT='peer_assessment',
    GROUP_REVIEW='group_review',
    GROUP_ASSESSMENT='group_assessment',
)


class GroupActivityStage(object):
    def __init__(self, doc_tree, grading_override):
        self.type = STAGE_TYPES.NORMAL

        self.grading_override = grading_override
        self._resources = []
        self._submissions = []
        self._questions = []
        self._assessments = []

        self.open_date = None
        self.close_date = None

        self.id = doc_tree.get("id")
        self.title = doc_tree.get("title")
        self.content = doc_tree.find("./content")
        self.upload = doc_tree.find("./upload")

        xml_type = doc_tree.get("type")
        if xml_type and xml_type in STAGE_TYPES.values():
            self.type = xml_type

        if doc_tree.get("open"):
            self.open_date = parse_date(doc_tree.get("open"))

        if doc_tree.get("close"):
            self.close_date = parse_date(doc_tree.get("close"))

        # import any questions
        for question in doc_tree.findall("./question"):
            question = GroupActivityQuestion(question, self)
            self._questions.append(question)

        # import any assessments
        for assessment in doc_tree.findall("./assessment"):
            self._assessments.append(GroupActivityAssessment(assessment))

        # import resources
        for document in doc_tree.findall("./resources/document"):
            self._resources.append(DottableDict({
                "title": document.get("title"),
                "description": document.get("description"),
                "location": document.text,
                "grading_criteria": document.get("grading_criteria") == "true"
            }))

        # import submission defintions
        for document in doc_tree.findall("./submissions/document"):
            self._submissions.append(DottableDict({
                "id": document.get("id"),
                "title": document.get("title"),
                "description": document.get("description"),
            }))

    @property
    def name(self):
        """
        Alias of title
        """
        return self.title

    @property
    def content_html(self):
        return inner_html(self.content)

    @property
    def questions(self):
        return tuple(self._questions)

    @property
    def assessments(self):
        return tuple(self._assessments)

    @property
    def resources(self):
        return tuple(self._resources)

    @property
    def submissions(self):
        return tuple(self._submissions)

    @property
    def grading_criteria(self):
        return (resource for resource in self._resources if resource.grading_criteria)

    @property
    def grade_questions(self):
        return (question for question in self._questions if question.grade)

    @staticmethod
    def formatted_date(date_value):
        return date_value.strftime("%m/%d/%Y")  # TODO: not l10n friendly

    # TODO: these four properties should be better named as has_*
    @property
    def peer_reviews(self):
        return self.type == STAGE_TYPES.PEER_REVIEW

    @property
    def other_group_reviews(self):
        return self.type == STAGE_TYPES.GROUP_REVIEW

    @property
    def peer_assessments(self):
        return self.type == STAGE_TYPES.PEER_ASSESSMENT

    @property
    def other_group_assessments(self):
        return self.type == STAGE_TYPES.GROUP_ASSESSMENT

    @property
    def formatted_open_date(self):
        return GroupActivityStage.formatted_date(self.open_date)

    @property
    def formatted_close_date(self):
        return GroupActivityStage.formatted_date(self.close_date)

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

    @property
    def is_upload_available(self):
        return self.submissions and self.is_open and not self.is_closed

    @property
    def has_submissions(self):
        return any([getattr(submission, 'location', None) for submission in self.submissions])

    # TODO: this method is used in presentation layer only - should remove it when possible
    @property
    def feedback_parameters(self):
        result = {}
        if self.type == STAGE_TYPES.PEER_REVIEW:
            result = dict(
                form_class='peer_review',
                form_action='submit_peer_feedback',
                input_id='peer_id'
            )
        elif self.type == STAGE_TYPES.GROUP_REVIEW:
            result = dict(
                form_class='other_group_review',
                form_action='submit_other_group_feedback',
                input_id='group_id'
            )

        return result

    @property
    def export_xml(self):
        return render_template('/templates/xml/activity_stage.xml', {"activity_stage": self})

    @property
    def render(self):
        return render_template('/templates/html/activity_stage.html', {"activity_stage": self})


class GroupActivityStageFactory(object):
    _type_map = {}

    _default_stage_class = GroupActivityStage

    @classmethod
    def create(cls, xml_node, grading_override):
        stage_type = xml_node.get("type")
        stage_class = cls._type_map.get(stage_type, cls._default_stage_class)

        return stage_class(xml_node, grading_override)

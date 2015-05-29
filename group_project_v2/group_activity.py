"""
This module parses Group project XML into a tree of domain-specific objects.
Basically it looks like the following

GroupActivity (.)
- GroupActivityStage (./activitystage)
-- GroupActivityQuestion (./activitystage/question)
--- <no dedicated class, etree.Element is used> (./activitystage/question/answer)
-- GroupActivityAssessment (./activitystage/assessment)
--- <no dedicated class, etree.Element is used> (./activitystage/assessment/answer)

GroupActivity (paths relative to root element)
- resources: [DottableDict(title, description, location)] - ./resources/document
# attribute filter implicit
- grading_criteria: [DottableDict(title, description, location)] - ./resources/document[@grading_criteria="true"]
- submissions: [DottableDict(id, title, description, location?)] - ./submissions/document
- grade_questions: [GroupActivityQuestion] - ./activitystage/question
- activity_stages: [GroupActivityStage] - ./activitystage
- grading_override: Bool                            # if True - allows visiting stages after close date; used by TA
* has_submissions: Bool                             # True if ANY submission uploaded
* has_all_submissions: Bool                         # True if ALL submission uploaded
* submission_json: json                             # submissions serialized into json format
* step_map: json
    {
        <stage_id>: { prev: prev_stage.id, name: stage.name, next: next_stage.id},
        ordered_list: [stage1.id, stage2.id, ...],
        default: <latest_open_stage.id if not grading_override else latest_stage_with_group_review_stage.id>
    }

GroupActivityStage (paths relative to ./activitystage)
-- id: str - ./@id
-- title: str - ./@title
-- type: str - ./@type                                      # governs stage behavior
-- content: etree.Element - ./content                       # HTML
-- open_date: datetime.date - ./@open
-- close_date: datetime.date - ./@close
-- activity: GroupActivity                                  # parent link
** questions: [ActivityQuestion] - ./question
** assessments: [ActivityAssessment] - ./assessment
** resources: [DottableDict(title, description, location, grading_criteria)] - ./submissions/resource
** submissions: [DottableDict(id, title, description, location?)] - ./submissions/document
** is_upload_available: Bool                                # IS upload stage and opened and not closed

GroupActivityQuestion (paths relative to //section/question)
---- id: str - ./@id
---- label: etree.Element - ./label
---- stage: GroupActivityStage                               # parent reference
---- answer: etree.Element - ./answer[0]                     # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                        # affects "answer" presentation - adds "side" class
---- required: Bool - ./@required                            # affects "question" presentation - adds "required" class
---- designer_class: [str] - ./@class                        # affects "question" presentation - added as is
---- question_classes: [str]                                 # ['question', designer_class?, "required"?]

GroupActivityAssessment (paths relative to //section/assessment)
---- id: str - ./@id
---- label: etree.Element ./label
---- answer: etree.Element = ./answer[0]                     # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                        # affects "answer" presentation - adds "side" class
"""
import itertools
import xml.etree.ElementTree as ET
from datetime import date
import copy
import json
from django.template.loader import render_to_string
from pkg_resources import resource_filename

from utils import render_template, DottableDict
from .project_api import _build_date_field


def parse_date(date_string):
    split_string = date_string.split('/')
    return date(int(split_string[2]), int(split_string[0]), int(split_string[1]))


def outer_html(node):
    if node is None:
        return None

    return ET.tostring(node, 'utf-8', 'html').strip()


def inner_html(node):
    if node is None:
        return None

    tag_length = len(node.tag)
    return outer_html(node)[tag_length + 2:-1 * (tag_length + 3)]


class GroupActivityQuestion(object):
    def __init__(self, doc_tree, stage):

        self.id = doc_tree.get("id")
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")
        self.stage = stage
        self.required = (doc_tree.get("required", "true") == "true")
        designer_class = doc_tree.get("class")
        self.question_classes = ["question"]
        self.grade = doc_tree.get("grade") == "true"

        if self.required:
            self.question_classes.append("required")
        if designer_class:
            self.question_classes.append(designer_class)

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        current_class = answer_node.get('class')
        answer_classes = ['answer']
        if current_class:
            answer_classes.append(current_class)
        if self.small:
            answer_classes.append('side')
        if self.stage.is_closed:
            answer_node.set('disabled', 'disabled')
        else:
            answer_classes.append('editable')
        answer_node.set('class', ' '.join(answer_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        label_html = ''
        label_node = copy.deepcopy(self.label)
        if len(inner_html(label_node)) > 0:
            label_node.set('for', self.id)
            current_class = label_node.get('class')
            label_classes = ['prompt']
            if current_class:
                label_classes.append(current_class)
            if self.small:
                label_classes.append('side')
            label_node.set('class', ' '.join(label_classes))
            label_html = outer_html(label_node)

        return '<div class="{}">{}{}</div>'.format(
            ' '.join(self.question_classes),
            label_html,
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html


class GroupActivityAssessment(object):
    def __init__(self, doc_tree):

        self.id = doc_tree.get("id")
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        answer_classes = ['answer']
        if self.small:
            answer_classes.append('side')
        current_class = answer_node.get('class')
        if current_class:
            answer_classes.append(current_class)
        answer_node.set('class', ' '.join(answer_classes))

        label_node = copy.deepcopy(self.label)
        label_node.set('for', self.id)
        current_class = label_node.get('class')
        label_classes = ['prompt']
        if current_class:
            label_classes.append(current_class)
        if self.small:
            label_classes.append('side')
        label_node.set('class', ' '.join(label_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        return "{}{}".format(
            outer_html(label_node),
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html


STAGE_TYPES = DottableDict(
    NORMAL='normal',
    UPLOAD='upload',
    PEER_REVIEW='peer_review',
    PEER_ASSESSMENT='peer_assessment',
    GROUP_REVIEW='group_review',
    GROUP_ASSESSMENT='group_assessment',
)


class GroupActivityStage(object):
    def __init__(self, doc_tree, activity):

        self.activity = activity
        self.grading_override = activity.grading_override
        self.type = STAGE_TYPES.NORMAL

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


class GroupActivity(object):
    def __init__(self, doc_tree, grading_override=False):
        self.activity_stages = []

        self.grading_override = grading_override

        # import project stage
        for stage in doc_tree.findall("./activitystage"):
            self.activity_stages.append(GroupActivityStage(stage, self))

    @property
    def resources(self):
        return itertools.chain(
            *[stage.resources for stage in self.activity_stages]
        )

    @property
    def submissions(self):
        return itertools.chain(
            *[stage.submissions for stage in self.activity_stages]
        )

    @property
    def grading_criteria(self):
        return itertools.chain(
            *[stage.grading_criteria for stage in self.activity_stages]
        )

    @property
    def grade_questions(self):
        return list(itertools.chain(
            *[stage.grade_questions for stage in self.activity_stages]
        ))

    def update_submission_data(self, submission_map):

        def formatted_date(iso_date_value):
            return GroupActivityStage.formatted_date(
                _build_date_field(iso_date_value)
            )

        for submission in self.submissions:
            if submission["id"] in submission_map:
                submission["location"] = submission_map[submission["id"]]["document_url"]
                submission["file_name"] = submission_map[submission["id"]]["document_filename"]
                submission["submission_date"] = formatted_date(submission_map[submission["id"]]["modified"])

    @property
    def export_xml(self):

        documents = copy.deepcopy(self.resources)
        dottable_documents = []
        for document in documents:
            document["grading_criteria"] = True if document in self.grading_criteria else None
            dottable_documents.append(DottableDict(document))

        data = {
            "documents": dottable_documents,
            "group_activity": self
        }

        return render_template('/templates/xml/group_activity.xml', data)

    @property
    def submission_json(self):
        submission_dicts = [submission.__dict__ for submission in self.submissions]
        return json.dumps(submission_dicts)

    @property
    def step_map(self):
        step_map = {}
        ordered_list = []
        prev_step = None
        default_stage = self.activity_stages[0].id
        for ac in self.activity_stages:
            step_map[ac.id] = {
                "prev": prev_step,
                "name": ac.name,
            }
            if not ac.is_open:
                step_map[ac.id]["restrict_message"] = "{} closed until {}".format(
                    ac.name,
                    ac.formatted_open_date
                )
            ordered_list.append(ac.id)
            prev_step = ac.id

            if self.grading_override:
                if ac.other_group_reviews:
                    default_stage = ac.id
            elif ac.open_date and ac.open_date <= date.today():
                default_stage = ac.id

        next_step = None
        for ac in reversed(self.activity_stages):
            step_map[ac.id]["next"] = next_step
            next_step = ac.id

        step_map["ordered_list"] = ordered_list
        step_map["default"] = default_stage

        return json.dumps(step_map)

    @property
    def has_submissions(self):
        uploaded_submissions = [s for s in self.submissions if hasattr(s, 'location') and s.location]
        return len(uploaded_submissions) > 0

    @property
    def has_all_submissions(self):
        uploaded_submissions = [s for s in self.submissions if hasattr(s, 'location') and s.location]
        return len(uploaded_submissions) == len(list(self.submissions))

    @classmethod
    def import_xml_file(cls, file_name):
        doc_tree = ET.parse(file_name).getroot()
        return cls(doc_tree)

    @classmethod
    def import_xml_string(cls, xml, grading_override=False):
        doc_tree = ET.fromstring(xml)
        return cls(doc_tree, grading_override)

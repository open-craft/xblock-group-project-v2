"""
This module parses Group project XML into a tree of domain-specific objects.
Basically it looks like the following

GroupActivity (.)
- GroupActivityStage (./activitystage)
-- GroupActivityStageSection (//section - different paths)
--- GroupActivityQuestion (//section/question)
---- <no dedicated class, etree.Element is used> (//section/question/answer)
--- GroupActivityAssessment (//section/assessment)
---- <no dedicated class, etree.Element is used> (//section/assessment/answer)

GroupActivity (paths relative to root element)
- resources: [DottableDict(title, description, location)] - ./resources/document
# attribute filter implicit
- grading_criteria: [DottableDict(title, description, location)] - ./resources/document[@grading_criteria="true"]
- submissions: [DottableDict(id, title, description, location?)] - ./submissions/document
- grade_questions: [GroupActivityQuestion] - //section/question
- activity_stages: [GroupActivityStage] - ./activitystage
- grading_override: Bool                            # if True - allows visiting stages after close date; used by TA
* has_submissions: Bool                             # True if ANY submission uploaded
* has_all_submissions: Bool                         # True if ALL submission uploaded
* submission_json: json                             # submissions serialized into json format
* step_map: json
    {
        <stage_id>: { prev: prev_stage.id, name: stage.name, next: next_stage.id},
        ordered_list: [stage1.id, stage2.id, ...],
        default: <latest_open_cstage.id if not grading_override else latest_stage_with_other_group_sections.id>
    }

GroupActivityStage (paths relative to ./activitystage)
-- id: str - ./@id
-- name: str - ./@name
-- sections: [ActivitySection] - ./section
-- peer_review_sections: [ActivitySection] - ./peerreview/section                     # reviewing teammates
-- peer_assessment_sections: [ActivitySection] - ./peerassessment/section             # assessing teammates' feedback
-- other_group_sections: [ActivitySection] - ./projectreview/section                  # reviewing other groups
-- other_group_assessment_sections: [ActivitySection] - ./projectassessment/section   # assessing other groups' feedback
-- open_date: datetime.date - @open
-- close_date: datetime.date - @close                                              # reference to milestone_dates key

GroupActivityStageSection (paths relative to (//section)
--- activity: GroupActivity                                          # grandparent reference
--- stage: GroupActivityStage                                    # parent reference
--- title: str - ./@title
--- upload_dialog: Bool - ./@upload_dialog
--- file_link_name: str - ./@file_links                                 # resources / submissions / grading_criteria
--- questions: [ActivityQuestion] - ./question
--- assessments: [ActivityAssessment] - ./assessment
--- content: etree.Element - ./content                                  # HTML
# if section IS NOT upload dialog gets links for resource, submission or grading_criteria files
*** file_links: [DottableDict(id?, title, description, location?)
# if section IS an upload dialog gets links for resource, submission or grading_criteria files
*** upload_links: [DottableDict(id?, title, description, location?)
# IS upload section and opened and not closed
*** is_upload_available: Bool

GroupActivityQuestion (paths relative to //section/question)
---- id: str - ./@id
---- label: etree.Element - ./label
---- section: ActivitySection                               # parent reference
---- answer: etree.Element - ./answer[0]                    # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                       # affects "answer" presentation - adds "side" class
---- required: Bool - ./@required                           # affects "question" presentation - adds "required" class
---- designer_class: [str] - ./@class                       # affects "question" presentation - added as is
---- question_classes: [str]                                # ['question', designer_class?, "required"?]

GroupActivityAssessment (paths relative to //section/assessment)
---- id: str - ./@id
---- label: etree.Element ./label
---- answer: etree.Element = ./answer[0]                    # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                       # affects "answer" presentation - adds "side" class
"""
import itertools
import xml.etree.ElementTree as ET
from datetime import date
import copy
import json
from django.template.loader import render_to_string
from pkg_resources import resource_filename

from utils import render_template
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


class DottableDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class GroupActivityQuestion(object):
    def __init__(self, doc_tree, section):

        self.id = doc_tree.get("id")
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")
        self.section = section
        self.required = (doc_tree.get("required", "true") == "true")
        designer_class = doc_tree.get("class")
        self.question_classes = ["question"]

        if self.required:
            self.question_classes.append("required")
        if designer_class:
            self.question_classes.append(designer_class)

        if doc_tree.get("grade") == "true":
            self.section.activity.grade_questions.append(self.id)

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
        if self.section.stage.is_closed:
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


class GroupActivityStageSection(object):
    def __init__(self, doc_tree, stage, activity):

        self.stage = stage
        self.questions = []
        self.assessments = []
        self.activity = activity

        self.title = doc_tree.get("title")
        self.content = doc_tree.find("./content")

        self.upload_dialog = (doc_tree.get("upload_dialog") == "true")

        self.file_link_name = doc_tree.get("file_links")

        # import any questions
        for question in doc_tree.findall("./question"):
            self.questions.append(GroupActivityQuestion(question, self))

        # import any assessments
        for assessment in doc_tree.findall("./assessment"):
            self.assessments.append(GroupActivityAssessment(assessment))

    @property
    def file_links(self):
        if self.upload_dialog:
            return None

        file_links = None
        if self.file_link_name:
            file_links = getattr(self.stage, self.file_link_name, None)

        return file_links

    @property
    def has_submissions(self):
        return len(
            [file_link for file_link in self.file_links if hasattr(file_link, 'location') and file_link.location]) > 0

    @property
    def upload_links(self):
        if not self.upload_dialog:
            return None

        file_links = None
        if self.file_link_name:
            file_links = getattr(self.stage, self.file_link_name, None)

        return file_links

    @property
    def content_html(self):
        if self.upload_dialog:
            return None
        return inner_html(self.content)

    @property
    def upload_html(self):
        if self.upload_dialog:
            return inner_html(self.content)
        return None

    @property
    def export_xml(self):
        data = {
            "activity_section": self,
        }
        return render_template('/templates/xml/activity_section.xml', data)

    @property
    def render(self):
        data = {
            "activity_section": self,
        }
        return render_template('/templates/html/activity_section.html', data)

    @property
    def is_upload_available(self):
        return self.upload_dialog and self.stage.is_open and not self.stage.is_closed


class GroupActivityStage(object):
    def __init__(self, doc_tree, activity):

        self.grading_override = activity.grading_override

        self._resources = []
        self._submissions = []

        self.sections = []
        self.peer_review_sections = []
        self.other_group_sections = []
        self.peer_assessment_sections = []
        self.other_group_assessment_sections = []
        self.open_date = None
        self.close_date = None

        self.name = doc_tree.get("name")
        self.id = doc_tree.get("id")

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

        # import submission defintions
        for document in doc_tree.findall("./submissions/document"):
            self._submissions.append(DottableDict({
                "id": document.get("id"),
                "title": document.get("title"),
                "description": document.get("description"),
            }))

        # import sections
        for section in doc_tree.findall("./section"):
            self.sections.append(GroupActivityStageSection(section, self, activity))

        # import questions for peer review
        for section in doc_tree.findall("./peerreview/section"):
            self.peer_review_sections.append(GroupActivityStageSection(section, self, activity))

        # import questions for project review
        for section in doc_tree.findall("./projectreview/section"):
            self.other_group_sections.append(GroupActivityStageSection(section, self, activity))

        # import questions for peer review
        for section in doc_tree.findall("./peerassessment/section"):
            self.peer_assessment_sections.append(GroupActivityStageSection(section, self, activity))

        # import questions for project review
        for section in doc_tree.findall("./projectassessment/section"):
            self.other_group_assessment_sections.append(GroupActivityStageSection(section, self, activity))

    @property
    def resources(self):
        return (resource for resource in self._resources if not resource.grading_criteria)

    @property
    def submissions(self):
        return self._submissions

    @property
    def grading_criteria(self):
        return (resource for resource in self._resources if resource.grading_criteria)

    @staticmethod
    def formatted_date(date_value):
        return date_value.strftime("%m/%d/%Y")  # TODO: not l10n friendly

    # TODO: these four properties should be better named as has_*
    @property
    def peer_reviews(self):
        return len(self.peer_review_sections) > 0

    @property
    def other_group_reviews(self):
        return len(self.other_group_sections) > 0

    @property
    def peer_assessments(self):
        return len(self.peer_assessment_sections) > 0

    @property
    def other_group_assessments(self):
        return len(self.other_group_assessment_sections) > 0

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
    def export_xml(self):
        data = {
            "activity_stage": self,
        }
        return render_template('/templates/xml/activity_stage.xml', data)


class GroupActivity(object):
    def __init__(self, doc_tree, grading_override=False):
        self.activity_stages = []

        self.grade_questions = []
        self.grading_override = grading_override

        # import project components
        for component in doc_tree.findall("./activitystage"):
            self.activity_stages.append(GroupActivityStage(component, self))

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
                if len(ac.other_group_sections) > 0:
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
        return len(uploaded_submissions) == len(self.submissions)

    @classmethod
    def import_xml_file(cls, file_name):
        doc_tree = ET.parse(file_name).getroot()
        return cls(doc_tree)

    @classmethod
    def import_xml_string(cls, xml, grading_override=False):
        doc_tree = ET.fromstring(xml)
        return cls(doc_tree, grading_override)

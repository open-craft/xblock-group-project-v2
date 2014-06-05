import xml.etree.ElementTree as ET
from datetime import date
import copy
import json
from django.template.loader import render_to_string
from pkg_resources import resource_filename

from utils import render_template

def outer_html(node):
    if node is None:
        return None

    return ET.tostring(node, 'utf-8', 'html').strip()

def inner_html(node):
    if node is None:
        return None

    tag_length = len(node.tag)
    return outer_html(node)[tag_length+2:-1*(tag_length+3)]

class DottableDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class ActivityQuestion(object):

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
        answer_class = 'answer'
        if self.small:
            answer_class = 'answer side'
        answer_node.set('class', answer_class)

        label_node = copy.deepcopy(self.label)
        label_node.set('for', self.id)
        label_class = 'prompt'
        if self.small:
            label_class = 'prompt side'
        label_node.set('class', label_class)

        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html)-1:
            ans_html = ans_html[:-1] + ' />'

        return "{}{}".format(
            outer_html(label_node),
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html)-1:
            html = html[:-1] + ' />'

        return html


class ActivityAssessment(object):

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
        answer_class = 'answer'
        if self.small:
            answer_class = 'answer side'
        answer_node.set('class', answer_class)

        label_node = copy.deepcopy(self.label)
        label_node.set('for', self.id)
        label_class = 'prompt'
        if self.small:
            label_class = 'prompt side'
        label_node.set('class', label_class)

        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html)-1:
            ans_html = ans_html[:-1] + ' />'

        return "{}{}".format(
            outer_html(label_node),
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html)-1:
            html = html[:-1] + ' />'

        return html

class ActivitySection(object):

    def __init__(self, doc_tree, activity):

        self.file_links = None
        self.questions = []
        self.assessments = []

        self.title = doc_tree.get("title")
        self.content = doc_tree.find("./content")

        self.file_link_name = doc_tree.get("file_links")
        if self.file_link_name:
            self.file_links = getattr(activity, self.file_link_name, None)

        # import any questions
        for question in doc_tree.findall("./question"):
            self.questions.append(ActivityQuestion(question))

        # import any assessments
        for assessment in doc_tree.findall("./assessment"):
            self.assessments.append(ActivityAssessment(assessment))

    @property
    def content_html(self):
        return inner_html(self.content)

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



class ActivityComponent(object):

    def __init__(self, doc_tree, activity):

        self.sections = []
        self.peer_review_sections = []
        self.other_group_sections = []
        self.peer_assessment_sections = []
        self.other_group_assessment_sections = []
        self.open_date = None
        self.open_date_name = None
        self.close_date = None
        self.close_date_name = None

        self.name = doc_tree.get("name")
        self.id = doc_tree.get("id")

        if doc_tree.get("open"):
            self.open_date_name = doc_tree.get("open")
            self.open_date = activity.milestone_dates[doc_tree.get("open")]

        if doc_tree.get("close"):
            self.close_date_name = doc_tree.get("close")
            self.close_date = activity.milestone_dates[doc_tree.get("close")]

        # import sections
        for section in doc_tree.findall("./section"):
            self.sections.append(ActivitySection(section, activity))

        # import questions for peer review
        for section in doc_tree.findall("./peerreview/section"):
            self.peer_review_sections.append(ActivitySection(section, activity))

        # import questions for project review
        for section in doc_tree.findall("./projectreview/section"):
            self.other_group_sections.append(ActivitySection(section, activity))

        # import questions for peer review
        for section in doc_tree.findall("./peerassessment/section"):
            self.peer_assessment_sections.append(ActivitySection(section, activity))

        # import questions for project review
        for section in doc_tree.findall("./projectassessment/section"):
            self.other_group_assessment_sections.append(ActivitySection(section, activity))

    @staticmethod
    def _formatted_date(date_value):
        return date_value.strftime("%m/%d/%Y")

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
        return ActivityComponent._formatted_date(self.open_date)

    @property
    def formatted_close_date(self):
        return ActivityComponent._formatted_date(self.close_date)

    @property
    def is_open(self):
        return (self.open_date is None) or (self.open_date <= date.today())

    @property
    def is_closed(self):
        return (self.close_date is not None) and (self.close_date < date.today())


    @property
    def export_xml(self):
        data = {
            "activity_component": self,
        }
        return render_template('/templates/xml/activity_component.xml', data)


class GroupActivity(object):

    @staticmethod
    def parse_date(date_string):
        split_string = date_string.split('/')
        return date(int(split_string[2]), int(split_string[0]), int(split_string[1]))

    def __init__(self, doc_tree):

        self.resources = []
        self.submissions = []
        self.activity_components = []
        self.grading_criteria = []
        self.milestone_dates = {}

        # import resources
        for document in doc_tree.findall("./resources/document"):
            document_info = DottableDict({
                "title": document.get("title"),
                "description": document.get("description"),
                "location": document.text,
            })
            self.resources.append(document_info)

            if document.get("grading_criteria") == "true":
                self.grading_criteria.append(document_info)

        # import milestone dates
        for milestone in doc_tree.findall("./dates/milestone"):
            self.milestone_dates.update({
                milestone.get("name"): self.parse_date(milestone.text)
            })

        # import submission defintions
        for document in doc_tree.findall("./submissions/document"):
            self.submissions.append(DottableDict({
                "id": document.get("id"),
                "title": document.get("title"),
                "description": document.get("description"),
            }))

        # import project components
        for component in doc_tree.findall("./projectcomponent"):
            self.activity_components.append(ActivityComponent(component, self))

    @property
    def export_xml(self):

        documents = copy.deepcopy(self.resources)
        dottable_documents = []
        for document in documents:
            document["grading_criteria"] = True if document in self.grading_criteria else None
            dottable_documents.append(DottableDict(document))

        milestones = [DottableDict({"name": key, "mmddyy": value.strftime("%m/%d/%Y")}) for key, value in self.milestone_dates.iteritems()]

        data = {
            "documents": dottable_documents,
            "milestones": milestones,
            "group_activity": self,
            "activity_component_path": resource_filename(__name__, 'templates/activity_component.xml')
        }

        return render_template('/templates/xml/group_activity.xml', data)

    @property
    def submission_json(self):
        submission_dicts = [submission.__dict__ for submission in self.submissions]
        return json.dumps(submission_dicts)


    @classmethod
    def import_xml_file(cls, file_name):
        doc_tree = ET.parse(file_name).getroot()
        return cls(doc_tree)

    @classmethod
    def import_xml_string(cls, xml):
        doc_tree = ET.fromstring(xml)
        return cls(doc_tree)


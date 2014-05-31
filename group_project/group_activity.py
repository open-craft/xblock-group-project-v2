import xml.etree.ElementTree as ET
from datetime import date
import copy
from django.template.loader import render_to_string
from pkg_resources import resource_filename

from utils import render_template

class DottableDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class ActivityQuestion(object):

    def __init__(self, doc_tree):

        self.id = doc_tree.get("id")
        self.label = doc_tree.find("./label").text
        self.answer = doc_tree.find("./answer")[0]

    def question_html(self):
        answer_node = copy.deepcopy(answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)

        label_node = copy.deepcopy(label)
        label_node.set('for', self.id)

        return "{}{}".format(
            ET.tostring(answer_node, 'utf-8', 'html'),
            ET.tostring(label_node, 'utf-8', 'html'),
        )


class ActivitySection(object):
    CONTENT_NAME = 'content'

    def __init__(self, doc_tree, activity):

        self.file_links = None
        self.questions = []

        self.title = doc_tree.get("title")
        self.content = doc_tree.find("./{}".format(self.CONTENT_NAME))

        self.file_link_name = doc_tree.get("file_links")
        if self.file_link_name:
            self.file_links = getattr(activity, self.file_link_name, None)

        # import any questions
        for question in doc_tree.findall("./question"):
            self.questions.append(ActivityQuestion(question))

    @property
    def content_html(self):
        return ET.tostring(self.content, 'utf-8', 'html')[len(self.CONTENT_NAME)+2:-1*(len(self.CONTENT_NAME)+3)]



class ActivityComponent(object):

    def __init__(self, doc_tree, activity):

        self.sections = []
        self.peer_review_sections = []
        self.other_group_sections = []
        self.open_date = None
        self.open_date_name = None
        self.close_date = None
        self.close_date_name = None

        self.name = doc_tree.get("name")

        if doc_tree.get("open"):
            self.open_date_name = doc_tree.get("open")
            self.open_date = activity.milestone_dates[doc_tree.get("open")]

        if doc_tree.get("close"):
            self.close_date_name = doc_tree.get("close")
            self.close_date = activity.milestone_dates[doc_tree.get("close")]

        # import sections
        for section in doc_tree.findall("section"):
            self.sections.append(ActivitySection(section, activity))

        # import questions for peer review
        for section in doc_tree.findall("peerreview/section"):
            self.peer_review_sections.append(ActivitySection(section, activity))

        # import questions for submission review
        for section in doc_tree.findall("submissionreview/section"):
            self.other_group_sections.append(ActivitySection(section, activity))

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
            document_info = {
                "title": document.get("title"),
                "description": document.get("description"),
                "location": document.text,
            }
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
            self.submissions.append({
                "id": document.get("id"),
                "title": document.get("title"),
                "description": document.get("description"),
            })

        # import project components
        for component in doc_tree.findall("./projectcomponent"):
            self.activity_components.append(ActivityComponent(component, self))

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


    @classmethod
    def import_xml_file(cls, file_name):
        doc_tree = ET.parse(file_name).getroot()
        return cls(doc_tree)

    @classmethod
    def import_xml_string(cls, xml):
        doc_tree = ET.fromstring(xml)
        return cls(doc_tree)


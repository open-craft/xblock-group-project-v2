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

from group_project_v2.group_stage import GroupActivityStage
from group_project_v2.utils import inner_html, outer_html, build_date_field
from utils import render_template, DottableDict
from .project_api import build_date_field


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
                build_date_field(iso_date_value)
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

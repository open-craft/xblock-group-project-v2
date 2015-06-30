import copy
import json
import itertools
import xml.etree.ElementTree as ET

from collections import Counter
from datetime import date

from ..utils import loader, DottableDict, format_date, gettext as _
from ..project_api import build_date_field

from .stage import GroupActivityStageFactory, GroupReviewStage, StageValidationMessage


class GroupActivity(object):
    def __init__(self, doc_tree, grading_override=False):
        self.activity_stages = []

        self.grading_override = grading_override

        # import project stage
        for stage in doc_tree.findall("./activitystage"):
            stage = GroupActivityStageFactory.create(stage, self.grading_override)
            self.activity_stages.append(stage)

    @property
    def resources(self):
        return itertools.chain(
            *[stage.resources for stage in self.activity_stages]
        )

    @property
    def submissions(self):
        return itertools.chain(
            *[getattr(stage, 'submissions', ()) for stage in self.activity_stages]
        )

    @property
    def grading_criteria(self):
        return itertools.chain(
            *[stage.grading_criteria for stage in self.activity_stages]
        )

    @property
    def grade_questions(self):
        return list(itertools.chain(
            *[getattr(stage, 'grade_questions', ()) for stage in self.activity_stages]
        ))

    def update_submission_data(self, submission_map):

        def formatted_date(iso_date_value):
            return format_date(build_date_field(iso_date_value))

        for submission in self.submissions:
            if submission["id"] in submission_map:
                new_submission_data = submission_map[submission["id"]]
                submission["location"] = new_submission_data["document_url"]
                submission["file_name"] = new_submission_data["document_filename"]
                submission["submission_date"] = formatted_date(new_submission_data["modified"])
                if "user_details" in new_submission_data:
                    submission["user_details"] = new_submission_data["user_details"]

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

        return loader.render_template('/templates/xml/group_activity.xml', data)

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
        for activity in self.activity_stages:
            step_map[activity.id] = {
                "prev": prev_step,
                "name": activity.name,
            }
            if not activity.is_open:
                step_map[activity.id]["restrict_message"] = "{} closed until {}".format(
                    activity.name,
                    activity.formatted_open_date
                )
            ordered_list.append(activity.id)
            prev_step = activity.id

            if self.grading_override:
                if isinstance(activity, GroupReviewStage):
                    default_stage = activity.id
            elif activity.open_date and activity.open_date <= date.today():
                default_stage = activity.id

        next_step = None
        for activity in reversed(self.activity_stages):
            step_map[activity.id]["next"] = next_step
            next_step = activity.id

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

    def _validate(self):
        violations = []

        ids_count = Counter([stage.id for stage in self.activity_stages])
        for stage_id, count in ids_count.iteritems():
            if count > 1:
                violations.append(StageValidationMessage(
                    StageValidationMessage.WARNING,
                    _(u"Duplicate stage ids: {stage_id} appeared {count} times").format(stage_id=stage_id, count=count)
                ))

        return violations

    def validate(self):
        return itertools.chain(
            self._validate(),
            *[stage.validate() for stage in self.activity_stages]
        )

# from django.test import TestCase
# from django import settings

import textwrap
from unittest import TestCase
from datetime import date
from group_project_v2.components import GroupActivity
from group_project_v2.components.stage import (
    BasicStage, SubmissionStage, PeerReviewStage, GroupReviewStage, PeerAssessmentStage, GroupAssessmentStage,
    ResourceType)


class GroupActivitityXmlTest(TestCase):
    def _assert_stage_name_and_type(self, stage, expected_title, expected_class):
        self.assertEqual(stage.title, expected_title)
        self.assertIsInstance(stage, expected_class)

    def _assert_stage_start_and_end_date(self, stage, expected_open, expected_close):
        self.assertEqual(stage.open_date, expected_open)
        self.assertEqual(stage.close_date, expected_close)

    def _assert_resources_submissions_and_grading(self, stage, resources=None, submissions=None, grading_criteria=None):
        def _check(attr_name, expected):
            if expected is not None:
                attr_value = getattr(stage, attr_name)
                self.assertEqual(len(list(attr_value)), expected)
            else:
                self.assertFalse(hasattr(stage, attr_name))

        _check('resources', resources)
        _check('submissions', submissions)
        _check('grading_criteria', grading_criteria)

    def _assert_stage_sections(self, stage, normal=0,
                               peer_review=0, group_review=0, peer_assessment=0, group_assessment=0):
        self.assertEqual(len(stage.sections), normal)
        self.assertEqual(len(stage.peer_review_sections), peer_review)
        self.assertEqual(len(stage.other_group_sections), group_review)
        self.assertEqual(len(stage.peer_assessment_sections), peer_assessment)
        self.assertEqual(len(stage.other_group_assessment_sections), group_assessment)

    # pylint: disable=too-many-statements
    def test_read_from_xml(self):
        grp_act = GroupActivity.import_xml_file('tests/xml/test.xml')

        resource_data = list(grp_act.resources)
        self.assertEqual(len(resource_data), 4)
        self.assertEqual(resource_data[0]["title"], "Issue Tree Template")
        self.assertEqual(resource_data[0]["description"], None)
        self.assertEqual(resource_data[0]["location"], "http://download/file.doc")
        self.assertEqual(resource_data[0]["type"], ResourceType.NORMAL)
        self.assertEqual(resource_data[1]["description"], "These are the instructions for this activity")
        self.assertEqual(resource_data[1]["type"], ResourceType.NORMAL)
        self.assertEqual(resource_data[2]["title"], "Video")
        self.assertEqual(resource_data[2]["location"], "0123456789abcdef")
        self.assertEqual(resource_data[2]["type"], ResourceType.OOYALA_VIDEO)

        grading_criteria_data = list(grp_act.grading_criteria)
        self.assertEqual(len(grading_criteria_data), 1)

        submissions_data = list(grp_act.submissions)
        self.assertEqual(len(submissions_data), 3)
        self.assertEqual(submissions_data[0]["id"], "issue_tree")
        self.assertEqual(submissions_data[0]["title"], "Issue Tree")
        self.assertEqual(submissions_data[0]["description"], None)
        self.assertEqual(submissions_data[2]["description"], "xls budget plan")

        stages = grp_act.activity_stages
        self.assertEqual(len(stages), 6)

        overview, upload, team_review, group_review, team_assessment, group_assessment = stages

        self._assert_stage_name_and_type(overview, "Overview", BasicStage)
        self._assert_stage_name_and_type(upload, "Upload", SubmissionStage)
        self._assert_stage_name_and_type(team_review, "Review Team", PeerReviewStage)
        self._assert_stage_name_and_type(group_review, "Review Group", GroupReviewStage)
        self._assert_stage_name_and_type(team_assessment, "Evaluate Team Feedback", PeerAssessmentStage)
        self._assert_stage_name_and_type(group_assessment, "Evaluate Group Feedback", GroupAssessmentStage)

        self._assert_stage_start_and_end_date(overview, None, None)
        self._assert_stage_start_and_end_date(upload, None, date(2014, 5, 24))
        self._assert_stage_start_and_end_date(team_review, date(2014, 5, 24), date(2014, 6, 20))
        self._assert_stage_start_and_end_date(group_review, date(2014, 5, 24), date(2014, 6, 20))
        self._assert_stage_start_and_end_date(team_assessment, date(2014, 6, 20), None)
        self._assert_stage_start_and_end_date(group_assessment, date(2014, 6, 20), None)

        self._assert_resources_submissions_and_grading(overview, resources=3, submissions=None, grading_criteria=0)
        self._assert_resources_submissions_and_grading(upload, resources=1, submissions=3, grading_criteria=1)
        self._assert_resources_submissions_and_grading(team_review, resources=0, submissions=None, grading_criteria=0)
        self._assert_resources_submissions_and_grading(group_review, resources=0, submissions=None, grading_criteria=0)

        self.assertEqual(list(overview.resources), resource_data[:3])

        self.assertEqual(textwrap.dedent(overview.content_html), textwrap.dedent(
            """
            <p>Html Description Blah Blah Blah<span>Additional info</span></p>
            <p>Html Description Blah Blah Blah</p>
            <p>Html Description Blah Blah Blah</p>
            <p>Html Description Blah Blah Blah</p>
            """))

        self.assertEqual(list(upload.submissions), submissions_data)

        self.assertEqual(team_review.questions[0].answer_html, '<input placeholder="answer here" type="text" />')

        self.assertEqual(team_review.questions[0].id, "score")
        self.assertEqual(team_review.questions[1].id, "q1")
        self.assertEqual(team_review.questions[2].id, "q2")
        self.assertEqual(team_review.questions[0].required, True)
        self.assertEqual(team_review.questions[1].required, True)
        self.assertEqual(team_review.questions[2].required, False)

        self.assertEqual(group_review.questions[0].id, "score")
        self.assertEqual(group_review.questions[1].id, "q1")
        self.assertEqual(group_review.questions[2].id, "q2")
        self.assertEqual(group_review.questions[0].required, True)
        self.assertEqual(group_review.questions[1].required, True)
        self.assertEqual(group_review.questions[2].required, True)

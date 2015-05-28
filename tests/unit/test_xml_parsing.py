# from django.test import TestCase
# from django import settings

import sys
from unittest import TestCase
from datetime import date
from group_project_v2.group_activity import GroupActivity, STAGE_TYPES


class GroupActivitityXmlTest(TestCase):
    def _assert_stage_name_and_type(self, stage, expected_name, expected_type):
        self.assertEqual(stage.name, expected_name)
        self.assertEqual(stage.type, expected_type)

    def _assert_stage_start_and_end_date(self, stage, expected_open, expected_close):
        self.assertEqual(stage.open_date, expected_open)
        self.assertEqual(stage.close_date, expected_close)

    def _assert_resources_submissions_and_grading(self, stage, resources=0, submissions=0, grading_criteria=0):
        self.assertEqual(len(list(stage.resources)), resources)
        self.assertEqual(len(list(stage.submissions)), submissions)
        self.assertEqual(len(list(stage.grading_criteria)), grading_criteria)

    def _assert_stage_sections(self, stage, normal=0,
                               peer_review=0, group_review=0, peer_assessment=0, group_assessment=0):
        self.assertEqual(len(stage.sections), normal)
        self.assertEqual(len(stage.peer_review_sections), peer_review)
        self.assertEqual(len(stage.other_group_sections), group_review)
        self.assertEqual(len(stage.peer_assessment_sections), peer_assessment)
        self.assertEqual(len(stage.other_group_assessment_sections), group_assessment)


    def test_read_from_xml(self):
        grp_act = GroupActivity.import_xml_file('tests/xml/test.xml')

        ir = list(grp_act.resources)
        self.assertEqual(len(ir), 2)
        self.assertEqual(ir[0]["title"], "Issue Tree Template")
        self.assertEqual(ir[0]["description"], None)
        self.assertEqual(ir[0]["location"], "http://download/file.doc")
        self.assertEqual(ir[1]["description"], "These are the instructions for this activity")

        gc = list(grp_act.grading_criteria)
        self.assertEqual(len(gc), 1)

        sr = list(grp_act.submissions)
        self.assertEqual(len(sr), 3)
        self.assertEqual(sr[0]["id"], "issue_tree")
        self.assertEqual(sr[0]["title"], "Issue Tree")
        self.assertEqual(sr[0]["description"], None)
        self.assertEqual(sr[2]["description"], "xls budget plan")

        ac = grp_act.activity_stages
        self.assertEqual(len(ac), 6)
        self._assert_stage_name_and_type(ac[0], "Overview", STAGE_TYPES.NORMAL)
        self._assert_stage_name_and_type(ac[1], "Upload", STAGE_TYPES.NORMAL)
        self._assert_stage_name_and_type(ac[2], "Review Team", STAGE_TYPES.PEER_REVIEW)
        self._assert_stage_name_and_type(ac[3], "Review Group", STAGE_TYPES.GROUP_REVIEW)
        self._assert_stage_name_and_type(ac[4], "Evaluate Team Feedback", STAGE_TYPES.PEER_ASSESSMENT)
        self._assert_stage_name_and_type(ac[5], "Evaluate Group Feedback", STAGE_TYPES.GROUP_ASSESSMENT)

        self._assert_stage_start_and_end_date(ac[0], None, None)
        self._assert_stage_start_and_end_date(ac[1], None, date(2014, 5, 24))
        self._assert_stage_start_and_end_date(ac[2], date(2014, 5, 24), date(2014, 6, 20))
        self._assert_stage_start_and_end_date(ac[3], date(2014, 5, 24), date(2014, 6, 20))
        self._assert_stage_start_and_end_date(ac[4], date(2014, 6, 20), None)
        self._assert_stage_start_and_end_date(ac[5], date(2014, 6, 20), None)

        self._assert_resources_submissions_and_grading(ac[0], resources=2, submissions=0, grading_criteria=0)
        self._assert_resources_submissions_and_grading(ac[1], resources=0, submissions=3, grading_criteria=1)
        self._assert_resources_submissions_and_grading(ac[2], resources=0, submissions=0, grading_criteria=0)
        self._assert_resources_submissions_and_grading(ac[3], resources=0, submissions=0, grading_criteria=0)

        self.assertEqual(len(ac[0].sections), 4)
        self.assertEqual(ac[0].sections[0].title, "Section Title")
        self.assertEqual(ac[0].sections[1].title, "Details")
        self.assertEqual(ac[0].sections[2].title, "Suggested Schedule")
        self.assertEqual(ac[0].sections[3].title, "Project Materials")

        pm = ac[0].sections[3]
        self.assertEqual(list(pm.file_links), ir)
        self.assertEqual(pm.file_link_name, "resources")

        self.assertNotEqual(ac[0].sections[0].content, None)
        self.assertEqual(ac[0].sections[0].content_html, "<p>Html Description Blah Blah Blah<span>Additional info</span></p>")

        sl = ac[1].sections[1]
        self.assertEqual(list(sl.file_links), sr)

        self._assert_stage_sections(ac[2], normal=1, peer_review=2)
        self._assert_stage_sections(ac[3], group_review=2)
        self._assert_stage_sections(ac[4], normal=1, peer_assessment=1)
        self._assert_stage_sections(ac[5], group_assessment=1)

        self.assertEqual(len(ac[2].sections), 1)
        self.assertEqual(len(ac[2].peer_review_sections), 2)
        self.assertEqual(len(ac[2].other_group_sections), 0)
        self.assertEqual(len(ac[3].other_group_sections), 2)
        self.assertEqual(len(ac[2].peer_review_sections[0].questions), 1)
        self.assertEqual(len(ac[2].peer_review_sections[1].questions), 2)

        self.assertEqual(ac[2].peer_review_sections[0].questions[0].answer_html, '<input placeholder="answer here" type="text" />')

        self.assertEqual(ac[2].peer_review_sections[1].questions[0].id, "q1")
        self.assertEqual(ac[2].peer_review_sections[1].questions[1].id, "q2")
        self.assertEqual(ac[2].peer_review_sections[1].questions[0].required, True)
        self.assertEqual(ac[2].peer_review_sections[1].questions[1].required, False)

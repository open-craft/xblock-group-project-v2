# from django.test import TestCase
# from django import settings

import sys
from unittest import TestCase
from datetime import date
from group_project_v2.group_activity import GroupActivity


class GroupActivitityXmlTest(TestCase):
    def test_read_from_xml(self):
        grp_act = GroupActivity.import_xml_file('tests/xml/test.xml')

        self.assertEqual(grp_act.milestone_dates["submissions"], date(2014, 5, 24))
        self.assertEqual(grp_act.milestone_dates["review"], date(2014, 6, 20))

        ir = grp_act.resources
        self.assertEqual(len(ir), 3)
        self.assertEqual(ir[0]["title"], "Issue Tree Template")
        self.assertEqual(ir[0]["description"], None)
        self.assertEqual(ir[0]["location"], "http://download/file.doc")
        self.assertEqual(ir[1]["description"], "These are the instructions for this activity")

        gc = grp_act.grading_criteria
        self.assertEqual(len(gc), 1)

        sr = grp_act.submissions
        self.assertEqual(len(sr), 3)
        self.assertEqual(sr[0]["id"], "issue_tree")
        self.assertEqual(sr[0]["title"], "Issue Tree")
        self.assertEqual(sr[0]["description"], None)
        self.assertEqual(sr[2]["description"], "xls budget plan")

        ac = grp_act.activity_components
        self.assertEqual(len(ac), 4)
        self.assertEqual(ac[0].name, "Overview")
        self.assertEqual(ac[1].name, "Upload")
        self.assertEqual(ac[2].name, "Review")
        self.assertEqual(ac[3].name, "Grade")

        self.assertEqual(len(ac[0].sections), 4)
        self.assertEqual(ac[0].sections[0].title, "Section Title")
        self.assertEqual(ac[0].sections[1].title, "Details")
        self.assertEqual(ac[0].sections[2].title, "Suggested Schedule")
        self.assertEqual(ac[0].sections[3].title, "Project Materials")

        pm = ac[0].sections[3]
        self.assertEqual(pm.file_links, ir)
        self.assertEqual(pm.file_link_name, "resources")

        self.assertNotEqual(ac[0].sections[0].content, None)
        self.assertEqual(ac[0].sections[0].content_html, "<p>Html Description Blah Blah Blah<span>Additional info</span></p>")

        sl = ac[1].sections[1]
        self.assertEqual(sl.file_links, sr)

        self.assertEqual(len(ac[2].sections), 1)
        self.assertEqual(len(ac[2].peer_review_sections), 2)
        self.assertEqual(len(ac[2].other_group_sections), 2)
        self.assertEqual(len(ac[2].peer_review_sections[0].questions), 1)
        self.assertEqual(len(ac[2].peer_review_sections[1].questions), 2)

        self.assertEqual(ac[2].peer_review_sections[0].questions[0].answer_html, '<input placeholder="answer here" type="text" />')

        self.assertEqual(ac[2].peer_review_sections[1].questions[0].id, "q1")
        self.assertEqual(ac[2].peer_review_sections[1].questions[1].id, "q2")
        self.assertEqual(ac[2].peer_review_sections[1].questions[0].required, True)
        self.assertEqual(ac[2].peer_review_sections[1].questions[1].required, False)

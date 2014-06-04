# from django.test import TestCase
# from django import settings

import sys
from datetime import date
from group_activity import GroupActivity

STOP_ON_ERROR = True

def test_equal(val1, val2):
    if val1 != val2:
        if STOP_ON_ERROR:
            raise Exception("FAILURE: {} does not equal {}".format(val1, val2))
        else:
            sys.stdout.write("\nFAILURE: {} does not equal {}\n".format(val1, val2))
    else:
        sys.stdout.write(".")

def test_not_equal(val1, val2):

    if val1 == val2:
        if STOP_ON_ERROR:
            raise Exception("FAILURE: {} does equals {}".format(val1, val2))
        else:
            sys.stdout.write("\nFAILURE: {} does equals {}\n".format(val1, val2))
    else:
        sys.stdout.write(".")


class GroupActivitityXmlTest(object):

    def test_read_from_xml(self):
        grp_act = GroupActivity.import_xml_file('test/test.xml')

        test_equal(grp_act.milestone_dates["submissions"], date(2014, 5, 24))
        test_equal(grp_act.milestone_dates["review"], date(2014, 6, 20))

        ir = grp_act.resources
        test_equal(len(ir), 3)
        test_equal(ir[0]["title"], "Issue Tree Template")
        test_equal(ir[0]["description"], None)
        test_equal(ir[0]["location"], "http://download/file.doc")
        test_equal(ir[1]["description"], "These are the instructions for this activity")

        gc = grp_act.grading_criteria
        test_equal(len(gc), 1)

        sr = grp_act.submissions
        test_equal(len(sr), 3)
        test_equal(sr[0]["id"], "issue_tree")
        test_equal(sr[0]["title"], "Issue Tree")
        test_equal(sr[0]["description"], None)
        test_equal(sr[2]["description"], "xls budget plan")

        ac = grp_act.activity_components
        test_equal(len(ac), 4)
        test_equal(ac[0].name, "Overview")
        test_equal(ac[1].name, "Upload")
        test_equal(ac[2].name, "Review")
        test_equal(ac[3].name, "Grade")

        test_equal(len(ac[0].sections), 4)
        test_equal(ac[0].sections[0].title, "Section Title")
        test_equal(ac[0].sections[1].title, "Details")
        test_equal(ac[0].sections[2].title, "Suggested Schedule")
        test_equal(ac[0].sections[3].title, "Project Materials")

        pm = ac[0].sections[3]
        test_equal(pm.file_links, ir)
        test_equal(pm.file_link_name, "resources")

        test_not_equal(ac[0].sections[0].content, None)
        test_equal(ac[0].sections[0].content_html, "<p>Html Description Blah Blah Blah<span>Additional info</span></p>")

        sl = ac[1].sections[1]
        test_equal(sl.file_links, sr)

        test_equal(len(ac[2].sections), 1)
        test_equal(len(ac[2].peer_review_sections), 2)
        test_equal(len(ac[2].other_group_sections), 2)
        test_equal(len(ac[2].peer_review_sections[0].questions), 1)
        test_equal(len(ac[2].peer_review_sections[1].questions), 2)

        test_equal(ac[2].peer_review_sections[0].questions[0].answer_html, '<input placeholder="answer here" type="text" />')
        #test_equal(ac[2].peer_review_sections[1].questions[0].answer_html, '<input placeholder="answer here" type="text" />')



if __name__ == "__main__":

    try:
        group_activity_test = GroupActivitityXmlTest()
        group_activity_test.test_read_from_xml()
    except Exception as e:
        sys.stdout.write("\n{}".format(e.message))
    finally:
        print
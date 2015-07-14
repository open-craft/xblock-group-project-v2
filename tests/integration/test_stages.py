"""
Tests for stage contents and interaction
"""
import datetime
import ddt
import textwrap
from freezegun import freeze_time
import mock

from group_project_v2.stage import StageType
from tests.integration.base_test import BaseIntegrationTest
from tests.integration.page_elements import GroupProjectElement, StageElement, ReviewStageElement
from tests.utils import KNOWN_USERS


class StageTestBase(BaseIntegrationTest):
    PROJECT_TEMPLATE = textwrap.dedent("""
        <group-project-v2 xmlns:opt="http://code.edx.org/xblock/option">
            <gp-v2-activity display_name="Activity">
                <opt:data>
                    <![CDATA[
                        <group_activity schema_version='1'>
                            <activitystage {stage_args}>
                                {stage_data}
                            </activitystage>
                        </group_activity>
                    ]]>
                </opt:data>
            </gp-v2-activity>
        </group-project-v2>
    """)
    stage_type = None
    page = None
    activity_id = None

    DEFAULT_STAGE_ID = 'stage_id'

    stage_element = StageElement

    def build_scenario_xml(self, stage_data, stage_id=DEFAULT_STAGE_ID, title="Stage Title", **kwargs):
        """
        Builds scenario XML with specified Stage parameters
        """
        stage_arguments = {'id': stage_id, 'title': title, 'type': self.stage_type}
        stage_arguments.update(kwargs)
        stage_args_str = " ".join(
            ["{}='{}'".format(arg_name, arg_value) for arg_name, arg_value in stage_arguments.iteritems()]
        )

        return self.PROJECT_TEMPLATE.format(stage_args=stage_args_str, stage_data=stage_data)

    def go_to_view(self, view_name='student_view', student_id=1):
        """
        Navigates to the page `view_name` as specified student
        Returns top-level Group Project element
        """
        scenario = super(StageTestBase, self).go_to_view(view_name=view_name, student_id=student_id)
        self.page = GroupProjectElement(self.browser, scenario)
        return self.page

    def get_stage(self, group_project):
        """
        Returns stage element wrapper
        """
        stage_element = group_project.activities[0].stages[0]
        self.activity_id = group_project.activities[0].id
        if self.stage_element != StageElement:
            stage_element = self.stage_element(self.browser, stage_element.element)
        self.assertTrue(stage_element.is_displayed())
        return stage_element

    def dismiss_message(self):
        """
        Clicks on "Ok" button in popup message dialog
        """
        button = self.browser.find_element_by_css_selector("div.message div.action_buttons button")
        button.click()


@ddt.ddt
class CommonStageTest(StageTestBase):
    """
    Tests common stage functionality
    """
    stage_type = StageType.NORMAL

    @ddt.data(
        # no open and close date - should be empty
        (datetime.datetime(2015, 1, 1), None, None, None),
        # no close, after open - should be empty
        (datetime.datetime(2015, 1, 2), datetime.datetime(2015, 1, 1), None, None),
        # no close, before open - should be opens Jan 02
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 2), None, "opens Jan 02"),
        # no close, before open, not same year - should be opens Jan 02 2015
        (datetime.datetime(2014, 1, 1), datetime.datetime(2015, 1, 2), None, "opens Jan 02 2015"),
        # no open, before close, should be due June 12
        (datetime.datetime(2015, 5, 12), None, datetime.datetime(2015, 6, 12), "due Jun 12"),
        # after open, before close, should be due June 12
        (datetime.datetime(2015, 5, 12), datetime.datetime(2015, 5, 1), datetime.datetime(2015, 6, 12), "due Jun 12"),
        # no open, before close, not same year - should be due June 12 2015
        (datetime.datetime(2014, 6, 22), None, datetime.datetime(2015, 6, 12), "due Jun 12 2015"),
        # after close - should be closed June 12
        (datetime.datetime(2015, 6, 13), None, datetime.datetime(2015, 6, 12), "closed on Jun 12"),
    )
    @ddt.unpack
    def test_open_close_label(self, mock_now, open_date, close_date, expected_label):
        date_format = "%m/%d/%Y"
        kwargs = {}
        if open_date is not None:
            kwargs['open'] = open_date.strftime(date_format)
        if close_date is not None:
            kwargs['close'] = close_date.strftime(date_format)

        with freeze_time(mock_now):
            scenario_xml = self.build_scenario_xml("", **kwargs)  # pylint: disable=star-args
            self.load_scenario_xml(scenario_xml)

            stage_element = self.get_stage(self.go_to_view())
            self.assertEqual(stage_element.open_close_label, expected_label)


@ddt.ddt
class NormalStageTest(StageTestBase):
    stage_type = StageType.NORMAL

    @ddt.data(
        "I'm content",
        "<p>I'm HTML content</p>",
        '<div><p>More complex<span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>'
    )
    def test_rendering(self, content):
        stage_content_xml = "<content>{content}</content>".format(content=content)
        self.load_scenario_xml(self.build_scenario_xml(stage_content_xml))

        stage_element = self.get_stage(self.go_to_view())
        stage_content = stage_element.content.get_attribute('innerHTML').strip()
        self.assertEqual(stage_content, content)


@ddt.ddt
class UploadStageTest(StageTestBase):
    stage_type = StageType.UPLOAD

    @ddt.data(
        "I'm content",
        "<p>I'm HTML content</p>",
        '<div><p>More complex<span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>'
    )
    def test_rendering(self, content):
        stage_content_xml = "<content>{content}</content>".format(content=content)
        scenario_xml = self.build_scenario_xml(stage_content_xml)
        self.load_scenario_xml(scenario_xml)

        stage_element = self.get_stage(self.go_to_view())
        stage_content = stage_element.content.get_attribute('innerHTML').strip()
        self.assertEqual(stage_content, content)


class BaseReviewStageTest(StageTestBase):
    workgroups_to_review = [
        {"id": 11, "name": "Group 1"}
    ]

    def setUp(self):
        super(BaseReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review.return_value = self.workgroups_to_review


@ddt.ddt
class PeerReviewStageTest(BaseReviewStageTest):
    stage_type = StageType.PEER_REVIEW
    stage_element = ReviewStageElement

    STAGE_DATA_XML = textwrap.dedent("""
        <grade_header>
            <h4>Evaluate <span class="username">this teammate</span></h4>
        </grade_header>
        <question id="peer_score">
            <label>How about that?</label>
            <answer>
                <input type="text" placeholder="answer here"/>
            </answer>
        </question>
        <question id="peer_q1">
            <label>Were they helpful?</label>
            <answer>
                <select>
                    <option value="Y">Yes</option>
                    <option value="N">No</option>
                </select>
            </answer>
        </question>
        <question id="peer_q2" required="false">
            <label>General Comments</label>
            <answer>
                <textarea/>
            </answer>
        </question>
    """)

    def setUp(self):
        super(PeerReviewStageTest, self).setUp()
        self.project_api_mock.get_peer_review_items = mock.Mock(return_value={})
        self.project_api_mock.get_peer_review_items_for_group = mock.Mock(return_value={})

        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML))

    def test_rendering_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        questions = stage_element.form.questions
        self.assertEqual(questions[0].label, "How about that?")
        self.assertEqual(questions[0].control.name, "peer_score")
        self.assertEqual(questions[0].control.tag_name, "input")
        self.assertEqual(questions[0].control.placeholder, "answer here")
        self.assertEqual(questions[0].control.type, "text")

        self.assertEqual(questions[1].label, "Were they helpful?")
        self.assertEqual(questions[1].control.name, "peer_q1")
        self.assertEqual(questions[1].control.tag_name, "select")
        self.assertEqual(questions[1].control.options, {"Y": "Yes", "N": "No"})

        self.assertEqual(questions[2].label, "General Comments")
        self.assertEqual(questions[2].control.name, "peer_q2")
        self.assertEqual(questions[2].control.tag_name, "textarea")

    @ddt.data(*KNOWN_USERS.keys())  # pylint: disable=star-args
    def test_interaction(self, user_id):
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        other_users = set(KNOWN_USERS.keys()) - {user_id}

        self.assertEqual(stage_element.form.peer_id, '')

        peers = stage_element.peers
        self.assertEqual(len(peers), len(other_users))
        for user_id, peer in zip(other_users, peers):
            self.assertEqual(peer.name, KNOWN_USERS[user_id]['username'])
            peer.click()
            self.assertEqual(stage_element.form.peer_id, str(user_id))

    @ddt.data(*KNOWN_USERS.keys())  # pylint: disable=star-args
    def test_submission(self, user_id):
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        peer = stage_element.peers[0]
        peer.click()

        expected_submissions = {
            "peer_score": "Very well",
            "peer_q1": "Y",
            "peer_q2": "Awesome"
        }

        questions = stage_element.form.questions
        questions[0].control.fill_text(expected_submissions["peer_score"])
        questions[1].control.select_option(expected_submissions["peer_q1"])
        questions[2].control.fill_text(expected_submissions["peer_q2"])

        self.assertTrue(stage_element.form.submit.is_displayed())
        self.assertEqual(stage_element.form.submit.text, "Submit")  # first time here - should read Submit
        stage_element.form.submit.click()

        self.project_api_mock.submit_peer_review_items.assert_called_once_with(
            str(user_id),
            stage_element.form.peer_id,
            1,
            self.activity_id,
            expected_submissions
        )

    def test_persistence_and_resubmission(self):
        user_id = 1
        expected_submissions = {
            "peer_score": "Very well",
            "peer_q1": "Y",
            "peer_q2": "Awesome"
        }

        self.project_api_mock.get_peer_review_items.return_value = [
            {"question": question, "answer": answer}
            for question, answer in expected_submissions.iteritems()
        ]

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        peer = stage_element.peers[0]
        peer.click()

        # loading peer review items from project_api
        self.project_api_mock.get_peer_review_items.assert_called_with(
            str(user_id),
            stage_element.form.peer_id,
            1,
            self.activity_id,
        )

        questions = stage_element.form.questions
        self.assertEqual(questions[0].control.value, expected_submissions["peer_score"])
        self.assertEqual(questions[1].control.value, expected_submissions["peer_q1"])
        self.assertEqual(questions[2].control.value, expected_submissions["peer_q2"])

        new_submissions = {
            "peer_score": "Terrible",
            "peer_q1": "N",
            "peer_q2": "Awful"
        }

        questions[0].control.fill_text(new_submissions["peer_score"])
        questions[1].control.select_option(new_submissions["peer_q1"])
        questions[2].control.fill_text(new_submissions["peer_q2"])

        self.assertEqual(stage_element.form.submit.text, "Resubmit")
        stage_element.form.submit.click()

        self.project_api_mock.submit_peer_review_items.assert_called_once_with(
            str(user_id),
            stage_element.form.peer_id,
            1,
            self.activity_id,
            new_submissions
        )

    def test_completion(self):
        user_id = 1
        other_users = set(KNOWN_USERS.keys()) - {user_id}
        expected_submissions = {
            "peer_score": "Very well",
            "peer_q1": "Y",
            "peer_q2": "Awesome"
        }

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        self.project_api_mock.get_peer_review_items_for_group.return_value = [
            {
                "question": question,
                "answer": answer,
                "workgroup": 1,
                "user": peer_id,
                "reviewer": str(user_id),
                "content_id": self.activity_id,
            }
            for question, answer in expected_submissions.iteritems()
            for peer_id in other_users
        ]

        peer = stage_element.peers[0]
        peer.click()

        questions = stage_element.form.questions
        questions[0].control.fill_text(expected_submissions["peer_score"])
        questions[1].control.select_option(expected_submissions["peer_q1"])
        questions[2].control.fill_text(expected_submissions["peer_q2"])
        stage_element.form.submit.click()

        self.project_api_mock.mark_as_complete.assert_called_with(
            'all',
            self.activity_id,
            user_id,
            self.DEFAULT_STAGE_ID
        )


@ddt.ddt
class GroupReviewStageTest(BaseReviewStageTest):
    stage_type = StageType.GROUP_REVIEW
    stage_element = ReviewStageElement

    OTHER_GROUPS = {
        2: {"id": 2, "name": "Group 2"},
        3: {"id": 3, "name": "Group 3"},
    }

    STAGE_DATA_XML = textwrap.dedent("""
        <question id="group_score">
            <label>How about that?</label>
            <answer>
                <input type="text" placeholder="answer here"/>
            </answer>
        </question>
        <question id="group_q1" grade="true">
            <label>Were they helpful?</label>
            <answer>
                <select>
                    <option value="100">Yes</option>
                    <option value="10">No</option>
                </select>
            </answer>
        </question>
        <question id="group_q2" required="false" grade="true">
            <label>General Comments</label>
            <answer>
                <textarea/>
            </answer>
        </question>
    """)

    def setUp(self):
        super(GroupReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review = mock.Mock(return_value=self.OTHER_GROUPS.values())
        self.project_api_mock.get_workgroup_review_items = mock.Mock(return_value={})
        self.project_api_mock.get_workgroup_review_items_for_group = mock.Mock(return_value={})
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(return_value=KNOWN_USERS.values())

        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML))

    def test_renderigng_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        questions = stage_element.form.questions
        self.assertEqual(questions[0].label, "How about that?")
        self.assertEqual(questions[0].control.name, "group_score")
        self.assertEqual(questions[0].control.tag_name, "input")
        self.assertEqual(questions[0].control.placeholder, "answer here")
        self.assertEqual(questions[0].control.type, "text")

        self.assertEqual(questions[1].label, "Were they helpful?")
        self.assertEqual(questions[1].control.name, "group_q1")
        self.assertEqual(questions[1].control.tag_name, "select")
        self.assertEqual(questions[1].control.options, {"100": "Yes", "10": "No"})

        self.assertEqual(questions[2].label, "General Comments")
        self.assertEqual(questions[2].control.name, "group_q2")
        self.assertEqual(questions[2].control.tag_name, "textarea")

    def test_interaction(self):
        stage_element = self.get_stage(self.go_to_view())

        self.assertEqual(stage_element.form.group_id, '')

        groups = stage_element.groups
        self.assertEqual(len(groups), len(self.OTHER_GROUPS.keys()))
        for group_id, group in zip(self.OTHER_GROUPS.keys(), groups):
            group.click()
            self.assertEqual(stage_element.form.group_id, str(group_id))

    def test_submission(self):
        user_id = 1
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        groups = stage_element.groups[0]
        groups.click()

        expected_submissions = {
            "group_score": "Very well",
            "group_q1": "100",
            "group_q2": "Awesome"
        }

        questions = stage_element.form.questions
        questions[0].control.fill_text(expected_submissions["group_score"])
        questions[1].control.select_option(expected_submissions["group_q1"])
        questions[2].control.fill_text(expected_submissions["group_q2"])

        self.assertTrue(stage_element.form.submit.is_displayed())
        self.assertEqual(stage_element.form.submit.text, "Submit")  # first time here - should read Submit

        stage_element.form.submit.click()

        self.project_api_mock.submit_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
            expected_submissions
        )

    def test_persistence_and_resubmission(self):
        user_id = 1
        expected_submissions = {
            "group_score": "Very well",
            "group_q1": "100",
            "group_q2": "Awesome"
        }

        self.project_api_mock.get_workgroup_review_items.return_value = [
            {"question": question, "answer": answer}
            for question, answer in expected_submissions.iteritems()
        ]

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        group = stage_element.groups[0]
        group.click()

        # loading peer review items from project_api
        self.project_api_mock.get_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
        )

        questions = stage_element.form.questions
        self.assertEqual(questions[0].control.value, expected_submissions["group_score"])
        self.assertEqual(questions[1].control.value, expected_submissions["group_q1"])
        self.assertEqual(questions[2].control.value, expected_submissions["group_q2"])

        new_submissions = {
            "group_score": "Terrible",
            "group_q1": "10",
            "group_q2": "Awful"
        }

        questions[0].control.fill_text(new_submissions["group_score"])
        questions[1].control.select_option(new_submissions["group_q1"])
        questions[2].control.fill_text(new_submissions["group_q2"])

        self.assertEqual(stage_element.form.submit.text, "Resubmit")
        stage_element.form.submit.click()

        self.project_api_mock.submit_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
            new_submissions
        )

    def test_completion(self):
        user_id = 1
        workgroups_to_review = self.OTHER_GROUPS.keys()
        expected_submissions = {
            "group_score": "Very well",
            "group_q1": "100",
            "group_q2": "200"
        }

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        self.project_api_mock.get_workgroup_review_items_for_group.return_value = [
            {
                "question": question,
                "answer": answer,
                "workgroup": group_id,
                "reviewer": str(reviewer_id),
                "content_id": self.activity_id,
            }
            for question, answer in expected_submissions.iteritems()
            for group_id in workgroups_to_review
            for reviewer_id in KNOWN_USERS.keys()
        ]

        groups = stage_element.groups[0]
        groups.click()

        questions = stage_element.form.questions
        questions[0].control.fill_text(expected_submissions["group_score"])
        questions[1].control.select_option(expected_submissions["group_q1"])
        questions[2].control.fill_text(expected_submissions["group_q2"])
        stage_element.form.submit.click()

        self.project_api_mock.mark_as_complete.assert_called_with(
            'all',
            self.activity_id,
            user_id,
            self.DEFAULT_STAGE_ID
        )

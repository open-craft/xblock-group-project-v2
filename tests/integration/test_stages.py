"""
Tests for stage contents and interaction
"""
import datetime
import ddt
import textwrap
from freezegun import freeze_time
import mock
from group_project_v2.stage import BasicStage, SubmissionStage, PeerReviewStage, TeamEvaluationStage

from tests.integration.base_test import BaseIntegrationTest
from tests.integration.page_elements import GroupProjectElement, StageElement, ReviewStageElement
from tests.utils import KNOWN_USERS


class StageTestBase(BaseIntegrationTest):
    PROJECT_TEMPLATE = textwrap.dedent("""
        <gp-v2-project xmlns:opt="http://code.edx.org/xblock/option">
            <gp-v2-activity display_name="Activity">
                <{stage_type} {stage_args}>
                    {stage_data}
                </{stage_type}>
            </gp-v2-activity>
        </gp-v2-project>
    """)
    stage_type = None
    page = None
    activity_id = None

    DEFAULT_STAGE_ID = 'stage_id'

    stage_element = StageElement

    def build_scenario_xml(self, stage_data, title="Stage Title", **kwargs):
        """
        Builds scenario XML with specified Stage parameters
        """
        stage_arguments = {'display_name': title}
        stage_arguments.update(kwargs)
        stage_args_str = " ".join(
            ["{}='{}'".format(arg_name, arg_value) for arg_name, arg_value in stage_arguments.iteritems()]
        )

        return self.PROJECT_TEMPLATE.format(
            stage_type=self.stage_type.CATEGORY,
            stage_args=stage_args_str, stage_data=stage_data
        )

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
    stage_type = BasicStage

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
        kwargs = {}
        if open_date is not None:
            kwargs['open_date'] = open_date.isoformat()
        if close_date is not None:
            kwargs['close_date'] = close_date.isoformat()

        with freeze_time(mock_now):
            scenario_xml = self.build_scenario_xml("", **kwargs)  # pylint: disable=star-args
            self.load_scenario_xml(scenario_xml)

            stage_element = self.get_stage(self.go_to_view())
            self.assertEqual(stage_element.open_close_label, expected_label)


@ddt.ddt
class NormalStageTest(StageTestBase):
    stage_type = BasicStage

    @ddt.data(
        ("I'm content", "I'm content"),
        ("<p>I'm HTML content</p>", "I'm HTML content"),
        (
            '<div><p>More complex <span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>',
            'More complex HTML content\nVery complex indeed'
        )
    )
    @ddt.unpack
    def test_rendering(self, content, expected_text):
        stage_content_xml = "<html>{content}</html>".format(content=content)
        self.load_scenario_xml(self.build_scenario_xml(stage_content_xml))

        stage_element = self.get_stage(self.go_to_view())
        stage_content = stage_element.content.text.strip()
        self.assertEqual(stage_content, expected_text)


@ddt.ddt
class UploadStageTest(StageTestBase):
    stage_type = SubmissionStage

    @ddt.data(
        ("I'm content", "I'm content"),
        ("<p>I'm HTML content</p>", "I'm HTML content"),
        (
            '<div><p>More complex <span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>',
            'More complex HTML content\nVery complex indeed'
        )
    )
    @ddt.unpack
    def test_rendering(self, content, expected_text):
        stage_content_xml = "<html>{content}</html>".format(content=content)
        scenario_xml = self.build_scenario_xml(stage_content_xml)
        self.load_scenario_xml(scenario_xml)

        stage_element = self.get_stage(self.go_to_view())
        stage_content = stage_element.content.text.strip()
        self.assertEqual(stage_content, expected_text)


class BaseReviewStageTest(StageTestBase):
    workgroups_to_review = [
        {"id": 11, "name": "Group 1"}
    ]

    def setUp(self):
        super(BaseReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review.return_value = self.workgroups_to_review


@ddt.ddt
class TeamEvaluationStageTest(BaseReviewStageTest):
    stage_type = TeamEvaluationStage
    stage_element = ReviewStageElement

    STAGE_DATA_XML = textwrap.dedent("""
        <gp-v2-peer-selector/>
        <gp-v2-review-question question_id="peer_score" title="How about that?" required="true" single_line="true">
          <opt:question_content>
            <![CDATA[
              <select>
                <option value="">Rating</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10</option>
              </select>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
        <gp-v2-review-question question_id="peer_q1" title="Were they helpful?" required="true" single_line="true">
          <opt:question_content>
            <![CDATA[
              <select>
                <option value="Y">Yes</option>
                <option value="N">No</option>
              </select>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
        <gp-v2-review-question question_id="peer_q2" title="General Comments" required="false">
          <opt:question_content>
            <![CDATA[
              <textarea/>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
    """)

    def setUp(self):
        super(TeamEvaluationStageTest, self).setUp()
        self.project_api_mock.get_peer_review_items = mock.Mock(return_value={})
        self.project_api_mock.get_peer_review_items_for_group = mock.Mock(return_value={})
        self.project_api_mock.get_user_organizations = mock.Mock(return_value=[{'display_name': "Org1"}])

        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML))

    def test_rendering_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        expected_options = {str(idx): str(idx) for idx in xrange(1, 11)}
        expected_options.update({"": "Rating"})

        questions = stage_element.form.questions
        self.assertEqual(questions[0].label, "How about that?")
        self.assertEqual(questions[0].control.name, "peer_score")
        self.assertEqual(questions[0].control.tag_name, "select")
        self.assertEqual(questions[0].control.options, expected_options)

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

        self.assertEqual(stage_element.form.peer_id, None)

        peers = stage_element.peers
        self.assertEqual(len(peers), len(other_users))
        for user_id, peer in zip(other_users, peers):
            self.assertEqual(peer.name, KNOWN_USERS[user_id]['username'])
            peer.click()
            self.assertEqual(stage_element.form.peer_id, user_id)

    @ddt.data(*KNOWN_USERS.keys())  # pylint: disable=star-args
    def test_submission(self, user_id):
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        peer = stage_element.peers[0]
        peer.click()

        expected_submissions = {
            "peer_score": "10",
            "peer_q1": "Y",
            "peer_q2": "Awesome"
        }

        questions = stage_element.form.questions
        questions[0].control.select_option(expected_submissions["peer_score"])
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
            "peer_score": "10",
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
            "peer_score": "2",
            "peer_q1": "N",
            "peer_q2": "Awful"
        }

        questions[0].control.select_option(new_submissions["peer_score"])
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
            "peer_score": "10",
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
        questions[0].control.select_option(expected_submissions["peer_score"])
        questions[1].control.select_option(expected_submissions["peer_q1"])
        questions[2].control.fill_text(expected_submissions["peer_q2"])
        stage_element.form.submit.click()

        self.project_api_mock.mark_as_complete.assert_called_with(
            'all',
            self.activity_id,
            user_id,
            stage_element.id
        )


@ddt.ddt
class PeerReviewStageTest(BaseReviewStageTest):
    stage_type = PeerReviewStage
    stage_element = ReviewStageElement

    OTHER_GROUPS = {
        2: {"id": 2, "name": "Group 2"},
        3: {"id": 3, "name": "Group 3"},
    }

    STAGE_DATA_XML = textwrap.dedent("""
        <gp-v2-group-selector/>
        <gp-v2-review-question question_id="group_score" title="How about that?" required="true" single_line="true">
          <opt:question_content>
            <![CDATA[
                <select>
                  <option value="">Grade</option>
                  <option value="0">0</option>
                  <option value="5">5</option>
                  <option value="10">10</option>
                  <option value="15">15</option>
                  <option value="20">20</option>
                  <option value="25">25</option>
                  <option value="30">30</option>
                  <option value="35">35</option>
                  <option value="40">40</option>
                  <option value="45">45</option>
                  <option value="50">50</option>
                  <option value="55">55</option>
                  <option value="60">60</option>
                  <option value="65">65</option>
                  <option value="70">70</option>
                  <option value="75">75</option>
                  <option value="80">80</option>
                  <option value="85">85</option>
                  <option value="90">90</option>
                  <option value="95">95</option>
                  <option value="100">100</option>
                </select>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
        <gp-v2-review-question question_id="group_q1" title="Were they helpful?" required="true" single_line="true">
          <opt:question_content>
            <![CDATA[
              <select>
                <option value="Y">Yes</option>
                <option value="N">No</option>
              </select>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
        <gp-v2-review-question question_id="group_q2" title="General Comments" required="false">
          <opt:question_content>
            <![CDATA[
              <textarea/>
            ]]>
          </opt:question_content>
        </gp-v2-review-question>
    """)

    def setUp(self):
        super(PeerReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review = mock.Mock(return_value=self.OTHER_GROUPS.values())
        self.project_api_mock.get_workgroup_review_items = mock.Mock(return_value={})
        self.project_api_mock.get_workgroup_review_items_for_group = mock.Mock(return_value={})
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(return_value=KNOWN_USERS.values())

        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML))

    def test_renderigng_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        expected_options = {str(idx): str(idx) for idx in xrange(0, 101, 5)}
        expected_options.update({"": "Grade"})

        questions = stage_element.form.questions
        self.assertEqual(questions[0].label, "How about that?")
        self.assertEqual(questions[0].control.name, "group_score")
        self.assertEqual(questions[0].control.tag_name, "select")
        self.assertEqual(questions[0].control.options, expected_options)

        self.assertEqual(questions[1].label, "Were they helpful?")
        self.assertEqual(questions[1].control.name, "group_q1")
        self.assertEqual(questions[1].control.tag_name, "select")
        self.assertEqual(questions[1].control.options, {"Y": "Yes", "N": "No"})

        self.assertEqual(questions[2].label, "General Comments")
        self.assertEqual(questions[2].control.name, "group_q2")
        self.assertEqual(questions[2].control.tag_name, "textarea")

    def test_interaction(self):
        stage_element = self.get_stage(self.go_to_view())

        self.assertEqual(stage_element.form.group_id, None)

        groups = stage_element.groups
        self.assertEqual(len(groups), len(self.OTHER_GROUPS.keys()))
        for group_id, group in zip(self.OTHER_GROUPS.keys(), groups):
            group.click()
            self.assertEqual(stage_element.form.group_id, group_id)

    def test_submission(self):
        user_id = 1
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        groups = stage_element.groups[0]
        groups.click()

        expected_submissions = {
            "group_score": "100",
            "group_q1": "Y",
            "group_q2": "Awesome"
        }

        questions = stage_element.form.questions
        questions[0].control.select_option(expected_submissions["group_score"])
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
            "group_score": "100",
            "group_q1": "Y",
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
            "group_score": "5",
            "group_q1": "N",
            "group_q2": "Awful"
        }

        questions[0].control.select_option(new_submissions["group_score"])
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
            "group_score": "100",
            "group_q1": "Y",
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
        questions[0].control.select_option(expected_submissions["group_score"])
        questions[1].control.select_option(expected_submissions["group_q1"])
        questions[2].control.fill_text(expected_submissions["group_q2"])
        stage_element.form.submit.click()

        self.project_api_mock.mark_as_complete.assert_called_with(
            'all',
            self.activity_id,
            user_id,
            stage_element.id
        )

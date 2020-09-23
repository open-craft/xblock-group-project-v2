"""
Tests for stage contents and interaction
"""
from builtins import zip
from builtins import str
from builtins import range
from collections import defaultdict

import datetime
import textwrap

import ddt
from freezegun import freeze_time
import mock
from workbench.runtime import WorkbenchRuntime

from group_project_v2.mixins import UserAwareXBlockMixin, AuthXBlockMixin
from group_project_v2.project_api.dtos import WorkgroupDetails
from group_project_v2.stage import BasicStage, SubmissionStage, PeerReviewStage, TeamEvaluationStage
from group_project_v2.stage.utils import ReviewState
from tests.integration.base_test import BaseIntegrationTest
from tests.integration.page_elements import GroupProjectElement, ReviewStageElement, ProjectTeamElement
from tests.utils import (
    KNOWN_USERS,
    OTHER_GROUPS,
    TestConstants,
    TestWithPatchesMixin,
    make_review_item as mri,
    WORKGROUP)


class StageTestBase(BaseIntegrationTest):
    PROJECT_TEMPLATE = textwrap.dedent("""
        <gp-v2-project xmlns:opt="http://code.edx.org/xblock/option">
            <gp-v2-activity display_name="Activity" {activity_args}>
                <{stage_type} {stage_args}>
                    {stage_data}
                </{stage_type}>
            </gp-v2-activity>
        </gp-v2-project>
    """)
    stage_type = None
    page = None

    def build_scenario_xml(self, stage_data, title="Stage Title", activity_kwargs=None, **kwargs):
        """
        Builds scenario XML with specified Stage parameters
        """
        if activity_kwargs is None:
            activity_kwargs = {}

        def format_args(arg_dict):
            return " ".join(
                ["{}='{}'".format(arg_name, arg_value) for arg_name, arg_value in arg_dict.items()])

        stage_arguments = {'display_name': title}
        stage_arguments.update(kwargs)
        stage_args_str = format_args(stage_arguments)
        activity_args = format_args(activity_kwargs)

        return self.PROJECT_TEMPLATE.format(
            stage_type=self.stage_type.CATEGORY,
            stage_args=stage_args_str, stage_data=stage_data,
            activity_args=activity_args
        )

    def go_to_view(self, view_name='student_view', student_id=1):
        """
        Navigates to the page `view_name` as specified student
        Returns top-level Group Project element
        """
        scenario = super(StageTestBase, self).go_to_view(view_name=view_name, student_id=student_id)
        self.page = GroupProjectElement(self.browser, scenario)
        return self.page

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
        # phase is open at the end of the close date day
        (datetime.datetime(2015, 6, 13, 23, 59), datetime.datetime(2015, 6, 11),
         datetime.datetime(2015, 6, 13), "due Jun 13"),
        # phase is closed at the day after close day
        (datetime.datetime(2015, 6, 14), datetime.datetime(2015, 6, 11),
         datetime.datetime(2015, 6, 13), "closed on Jun 13"),
    )
    @ddt.unpack
    def test_open_close_label(self, mock_now, open_date, close_date, expected_label):
        kwargs = {}
        if open_date is not None:
            kwargs['open_date'] = open_date.isoformat()
        if close_date is not None:
            kwargs['close_date'] = close_date.isoformat()

        with freeze_time(mock_now):
            scenario_xml = self.build_scenario_xml("", **kwargs)
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

    def select_review_subject(self, subject):
        subject.click()
        self.wait_for_ajax()

    def setUp(self):
        super(BaseReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review.return_value = self.workgroups_to_review

    def click_submit(self, stage_element):
        stage_element.form.submit.click()
        self.wait_for_ajax()

    def submit_and_assert_completion_published(self, stage_element, user_id):
        with mock.patch('workbench.runtime.WorkbenchRuntime.publish') as patched_publish:
            self.click_submit(stage_element)

            self.assertTrue(patched_publish.called)

            call_args, call_kwargs = patched_publish.call_args
            self.assertEqual(call_kwargs, {})
            self.assertEqual(len(call_args), 3)

            block, event_type, event_data = call_args
            self.assertEqual(block.id, stage_element.id)
            self.assertEqual(event_type, 'progress')
            self.assertEqual(event_data, {'user_id': user_id})


@ddt.ddt
class TeamEvaluationStageTest(BaseReviewStageTest, TestWithPatchesMixin):
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

    REQUIRED_QUESTION_ID1 = "peer_score"
    REQUIRED_QUESTION_ID2 = "peer_q1"

    def setUp(self):
        super(TeamEvaluationStageTest, self).setUp()
        self.make_patch(TeamEvaluationStage, 'anonymous_student_id', mock.Mock(return_value="Farhaan"))
        self.project_api_mock.get_peer_review_items = mock.Mock(return_value={})

        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML), load_immediately=False)

    def _setup_review_items_store(self, initial_items=None):
        store = defaultdict(list)
        if initial_items:
            store.update(initial_items)

        def get_review_items(_reviewer_id, peer_id, _group_id, _content_id):
            return store.get(peer_id, [])

        def submit_peer_review_items(reviewer_id, peer_id, group_id, content_id, data):
            new_items = [
                mri(reviewer_id, question_id, peer=peer_id, content_id=content_id, answer=answer, group=group_id)
                for question_id, answer in data.items()
                if len(answer) > 0
            ]
            store[peer_id].extend(new_items)

        self.project_api_mock.get_peer_review_items = mock.Mock(side_effect=get_review_items)
        self.project_api_mock.submit_peer_review_items = mock.Mock(side_effect=submit_peer_review_items)

    def _assert_teammate_statuses(self, stage_element, expected_statuses):
        teammate_statuses = {int(peer.subject_id): peer.review_status for peer in stage_element.peers}
        self.assertEqual(teammate_statuses, expected_statuses)

    def test_rendering_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        expected_options = {str(idx): str(idx) for idx in range(1, 11)}
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

    def test_teammate_review_statuses(self):
        user_id = TestConstants.Users.USER1_ID
        reviews = {
            TestConstants.Users.USER2_ID: [
                mri(user_id, self.REQUIRED_QUESTION_ID1, peer=TestConstants.Users.USER2_ID, answer='not empty'),
            ],
            TestConstants.Users.USER3_ID: [
                mri(user_id, self.REQUIRED_QUESTION_ID1, peer=TestConstants.Users.USER3_ID, answer='not empty'),
                mri(user_id, self.REQUIRED_QUESTION_ID2, peer=TestConstants.Users.USER3_ID, answer='other')
            ],
        }
        self._setup_review_items_store(reviews)

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        expected_statuses = {
            TestConstants.Users.USER2_ID: ReviewState.INCOMPLETE,
            TestConstants.Users.USER3_ID: ReviewState.COMPLETED
        }
        self._assert_teammate_statuses(stage_element, expected_statuses)

    # pylint: disable=consider-iterating-dictionary
    @ddt.data(*list(KNOWN_USERS.keys()))
    def test_interaction(self, user_id):
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        other_users = set(KNOWN_USERS.keys()) - {user_id}

        # A default selection should be made automatically.
        self.assertEqual(stage_element.form.peer_id, min(other_users))

        peers = stage_element.peers
        self.assertEqual(len(peers), len(other_users))
        for peer_user_id, peer in zip(other_users, peers):
            self.assertEqual(peer.name, KNOWN_USERS[peer_user_id].username)
            self.select_review_subject(peer)
            self.assertEqual(stage_element.form.peer_id, peer_user_id)

    # pylint: disable=consider-iterating-dictionary
    @ddt.data(*list(KNOWN_USERS.keys()))
    def test_submission(self, user_id):
        self.make_patch(TeamEvaluationStage, 'anonymous_student_id', str(user_id))
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))
        self._setup_review_items_store()

        initial_statuses = {usr_id: ReviewState.NOT_STARTED for usr_id in list(KNOWN_USERS.keys()) if usr_id != user_id}
        self._assert_teammate_statuses(stage_element, initial_statuses)  # precondition check

        peer = stage_element.peers[0]
        self.select_review_subject(peer)

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
        self.click_submit(stage_element)

        self.project_api_mock.submit_peer_review_items.assert_called_once_with(
            str(user_id),
            stage_element.form.peer_id,
            1,
            self.activity_id,
            expected_submissions
        )

        expected_statuses = {usr_id: ReviewState.NOT_STARTED
                             for usr_id in KNOWN_USERS.keys() if usr_id != user_id}
        expected_statuses[int(peer.subject_id)] = ReviewState.COMPLETED  # status is refreshed after submission
        self._assert_teammate_statuses(stage_element, expected_statuses)

    def test_persistence_and_resubmission(self):
        user_id = 1
        self.make_patch(TeamEvaluationStage, 'anonymous_student_id', str(user_id))
        expected_submissions = {
            "peer_score": "10",
            "peer_q1": "Y",
            "peer_q2": "Awesome"
        }
        self.project_api_mock.get_peer_review_items.return_value = [
            {"question": question, "answer": answer, "user": TestConstants.Users.USER2_ID}
            for question, answer in expected_submissions.items()
        ]

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        peer = stage_element.peers[0]
        self.select_review_subject(peer)

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
        self.click_submit(stage_element)

        self.project_api_mock.submit_peer_review_items.assert_called_once_with(
            str(user_id),
            stage_element.form.peer_id,
            1,
            self.activity_id,
            new_submissions
        )

    def test_completion(self):
        user_id = 1
        self.make_patch(TeamEvaluationStage, 'anonymous_student_id', str(user_id))
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
            for question, answer in expected_submissions.items()
            for peer_id in other_users
        ]

        peer = stage_element.peers[0]
        self.select_review_subject(peer)

        questions = stage_element.form.questions
        self.wait_for_ajax()
        questions[0].control.select_option(expected_submissions["peer_score"])
        questions[1].control.select_option(expected_submissions["peer_q1"])
        questions[2].control.fill_text(expected_submissions["peer_q2"])

        self.submit_and_assert_completion_published(stage_element, user_id)


class BasePeerReviewStageTest(BaseReviewStageTest):

    stage_type = PeerReviewStage
    stage_element = ReviewStageElement

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

    REQUIRED_QUESTION_ID1 = 'group_score'
    REQUIRED_QUESTION_ID2 = 'group_q1'

    def setUp(self):
        super(BasePeerReviewStageTest, self).setUp()
        self.project_api_mock.get_workgroups_to_review = mock.Mock(return_value=list(OTHER_GROUPS.values()))
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(return_value=[
            {"id": user.id} for user in KNOWN_USERS.values()
        ])

    def _setup_review_items_store(self, initial_items=None):
        store = defaultdict(list)
        if initial_items:
            store.update(initial_items)

        def get_review_items(_reviewer_id, group_id, _content_id):
            return store.get(group_id, [])

        def submit_review_items(reviewer_id, group_id, content_id, data):
            new_items = [
                mri(reviewer_id, question_id, content_id=content_id, answer=answer, group=group_id)
                for question_id, answer in data.items()
                if len(answer) > 0
            ]
            store[group_id].extend(new_items)

        self.project_api_mock.get_workgroup_review_items = mock.Mock(side_effect=get_review_items)
        self.project_api_mock.submit_workgroup_review_items = mock.Mock(side_effect=submit_review_items)

    def _assert_group_statuses(self, stage_element, expected_statuses):
        group_statuses = {int(group.subject_id): group.review_status for group in stage_element.groups}
        self.assertEqual(group_statuses, expected_statuses)


@ddt.ddt
class PeerReviewStageTest(BasePeerReviewStageTest, TestWithPatchesMixin):
    def setUp(self):
        super(PeerReviewStageTest, self).setUp()
        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML), load_immediately=False)

    def test_renderigng_questions(self):
        stage_element = self.get_stage(self.go_to_view())

        expected_options = {str(idx): str(idx) for idx in range(0, 101, 5)}
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

    def test_group_statuses(self):
        user_id = TestConstants.Users.USER1_ID
        reviews = {
            TestConstants.Groups.GROUP2_ID: [
                mri(user_id, self.REQUIRED_QUESTION_ID1, group=TestConstants.Groups.GROUP2_ID, answer='not empty'),
            ],
            TestConstants.Groups.GROUP3_ID: [
                mri(user_id, self.REQUIRED_QUESTION_ID1, group=TestConstants.Groups.GROUP3_ID, answer='not empty'),
                mri(user_id, self.REQUIRED_QUESTION_ID2, group=TestConstants.Groups.GROUP3_ID, answer='other')
            ],
        }

        self._setup_review_items_store(reviews)

        self.project_api_mock.get_workgroup_reviewers = mock.Mock(return_value=[{"id": user_id}])
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))

        expected_statuses = {
            TestConstants.Groups.GROUP2_ID: ReviewState.INCOMPLETE,
            TestConstants.Groups.GROUP3_ID: ReviewState.COMPLETED
        }
        self._assert_group_statuses(stage_element, expected_statuses)

    def test_interaction(self):
        stage_element = self.get_stage(self.go_to_view())

        # A default selection should be made automatically.
        self.assertIn(stage_element.form.group_id, OTHER_GROUPS)

        groups = stage_element.groups
        self.assertEqual(len(groups), len(list(OTHER_GROUPS.keys())))
        for group_id, group in zip(list(OTHER_GROUPS.keys()), groups):
            self.select_review_subject(group)
            self.assertEqual(stage_element.form.group_id, group_id)

    def test_submission(self):
        user_id = TestConstants.Users.USER1_ID
        self.make_patch(PeerReviewStage, 'anonymous_student_id', str(user_id))
        stage_element = self.get_stage(self.go_to_view(student_id=user_id))
        self._setup_review_items_store()

        group = stage_element.groups[0]
        initial_statuses = {
            TestConstants.Groups.GROUP2_ID: ReviewState.NOT_STARTED,
            TestConstants.Groups.GROUP3_ID: ReviewState.NOT_STARTED
        }
        self._assert_group_statuses(stage_element, initial_statuses)
        self.select_review_subject(group)

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

        self.click_submit(stage_element)

        self.project_api_mock.submit_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
            expected_submissions
        )

        expected_statuses = {
            TestConstants.Groups.GROUP2_ID: ReviewState.COMPLETED,  # status is refreshed after submission
            TestConstants.Groups.GROUP3_ID: ReviewState.NOT_STARTED
        }
        self._assert_group_statuses(stage_element, expected_statuses)

    def test_persistence_and_resubmission(self):
        user_id = 1
        self.make_patch(PeerReviewStage, 'anonymous_student_id', str(user_id))
        expected_submissions = {
            "group_score": "100",
            "group_q1": "Y",
            "group_q2": "Awesome"
        }

        self.project_api_mock.get_workgroup_review_items.return_value = [
            {"question": question, "answer": answer, "workgroup": TestConstants.Groups.GROUP2_ID}
            for question, answer in expected_submissions.items()
        ]

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))
        self.assertFalse(stage_element.has_admin_grading_notification)

        group = stage_element.groups[0]
        self.select_review_subject(group)

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
        self.click_submit(stage_element)

        self.project_api_mock.submit_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
            new_submissions
        )

    def test_completion(self):
        user_id = 1
        self.make_patch(PeerReviewStage, 'anonymous_student_id', str(user_id))
        workgroups_to_review = list(OTHER_GROUPS.keys())
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
            for question, answer in expected_submissions.items()
            for group_id in workgroups_to_review
            for reviewer_id in KNOWN_USERS
        ]

        group = stage_element.groups[0]
        self.select_review_subject(group)

        questions = stage_element.form.questions
        questions[0].control.select_option(expected_submissions["group_score"])
        questions[1].control.select_option(expected_submissions["group_q1"])
        questions[2].control.fill_text(expected_submissions["group_q2"])

        self.submit_and_assert_completion_published(stage_element, user_id)


class TestTAGradedPeerReview(BasePeerReviewStageTest, TestWithPatchesMixin):
    def setUp(self):
        super(TestTAGradedPeerReview, self).setUp()

        self.project_api_mock.get_user_preferences = mock.Mock(return_value={
            "TA_REVIEW_WORKGROUP": [WORKGROUP.id]
        })
        self.project_api_mock.get_user_roles_for_course = mock.Mock(return_value={"assistant"})

    def __prepare_scenario_for_peer_graded_activity(self):
        activity_kwargs = dict(group_reviews_required_count=1)
        xml = self.build_scenario_xml(self.STAGE_DATA_XML, activity_kwargs=activity_kwargs)
        self.load_scenario_xml(xml, load_immediately=False)

    def __prepare_scenario_for_ta_graded_activity(self):
        activity_kwargs = dict(group_reviews_required_count=0)
        xml = self.build_scenario_xml(self.STAGE_DATA_XML, activity_kwargs=activity_kwargs)
        self.load_scenario_xml(xml, load_immediately=False)

    def test_ta_override_header(self):
        self.__prepare_scenario_for_peer_graded_activity()
        user_id = 1
        page = self.go_to_view(student_id=user_id)
        stage_element = self.get_stage(page)

        element = stage_element.element.find_element_by_css_selector('div.grading_override')

        self.assertEqual(element.text, 'TA Grading override view')
        self.assertNotIn("ta_graded", element.get_attribute('class'))

    def test_ta_grading_header(self):
        self.__prepare_scenario_for_ta_graded_activity()
        user_id = 1
        page = self.go_to_view(student_id=user_id)
        stage_element = self.get_stage(page)

        element = stage_element.element.find_element_by_css_selector('div.grading_override')

        self.assertEqual(element.text, 'Grading View')
        self.assertIn("ta_graded", element.get_attribute('class'))

    def test_ta_grading(self):
        self.__prepare_scenario_for_ta_graded_activity()
        user_id, group_id = 22, 3
        self.make_patch(PeerReviewStage, 'anonymous_student_id', str(user_id))
        self.project_api_mock.get_user_preferences = mock.Mock(
            return_value={UserAwareXBlockMixin.TA_REVIEW_KEY: group_id}
        )
        self.project_api_mock.get_user_roles_for_course = mock.Mock(return_value=set(AuthXBlockMixin.DEFAULT_TA_ROLE))
        self.project_api_mock.get_workgroup_by_id.side_effect = lambda g_id: WorkgroupDetails(
            id=g_id, users=[{"id": 1}]
        )

        stage_element = self.get_stage(self.go_to_view(student_id=user_id))
        self.assertTrue(stage_element.has_admin_grading_notification)

        self.project_api_mock.get_workgroup_by_id.assert_called_with(group_id)

        self.assertEqual(len(stage_element.groups), 1)
        group = stage_element.groups[0]
        self.assertEqual(group.subject_id, str(group_id))

        self.select_review_subject(group)

        submissions = {
            "group_score": "100",
            "group_q1": "Y",
            "group_q2": "Awesome"
        }

        questions = stage_element.form.questions
        questions[0].control.select_option(submissions["group_score"])
        questions[1].control.select_option(submissions["group_q1"])
        questions[2].control.fill_text(submissions["group_q2"])

        self.assertTrue(stage_element.form.submit.is_displayed())
        self.assertEqual(stage_element.form.submit.text, "Submit")  # first time here - should read Submit

        # mocking response after submitting
        self.project_api_mock.get_workgroup_review_items_for_group.return_value = [
            {"reviewer": str(user_id), "answer": answer, 'question': question, "workgroup": stage_element.form.group_id}
            for question, answer in submissions.items()
        ]

        with mock.patch.object(WorkbenchRuntime, 'publish') as patched_method:
            self.click_submit(stage_element)

            self.assertTrue(patched_method.called)
            publish_args, publish_kwargs = patched_method.call_args
            self.assertEqual(publish_kwargs, {})
            self.assertIsInstance(publish_args[0], PeerReviewStage)
            self.assertEqual(publish_args[0].id, stage_element.id)
            self.assertEqual(publish_args[1], 'progress')
            self.assertEqual(publish_args[2], {'user_id': user_id})

        self.project_api_mock.submit_workgroup_review_items.assert_called_with(
            str(user_id),
            stage_element.form.group_id,
            self.activity_id,
            submissions
        )


class ProjectTeamBlockTest(StageTestBase):
    """
    Tests the Project Team block
    """

    stage_type = BasicStage

    STAGE_DATA_XML = textwrap.dedent("""
        <gp-v2-project-team />
    """)

    def setUp(self):
        super(ProjectTeamBlockTest, self).setUp()
        self.load_scenario_xml(self.build_scenario_xml(self.STAGE_DATA_XML))

    def test_block_renders(self):
        """
        Ensure block shows team members.
        """
        user_id = 1
        self.project_api_mock.get_user_roles_for_course = mock.Mock(return_value=set(AuthXBlockMixin.DEFAULT_TA_ROLE))
        self.project_api_mock.get_workgroup_by_id.side_effect = lambda g_id: {"id": g_id, "users": [{"id": 1}]}
        stage_element = self.get_stage(self.go_to_view(student_id=user_id), stage_element_type=ProjectTeamElement)
        self.assertEqual(stage_element.team_members, [u'Jane', u'Jack', u'Jill'])

"""
Tests for project navigator and its views
"""
import logging
import textwrap
import ddt
import mock

from group_project_v2.project_navigator import (
    ViewTypes, ResourcesViewXBlock, SubmissionsViewXBlock, AskTAViewXBlock, PrivateDiscussionViewXBlock
)
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage,
    StageState
)
from tests.integration.base_test import SingleScenarioTestSuite, BaseIntegrationTest
from tests.integration.page_elements import NavigationViewElement, ResourcesViewElement, SubmissionsViewElement, \
    GroupProjectElement
from tests.utils import KNOWN_USERS, TestWithPatchesMixin


class TestProjectNavigatorViews(SingleScenarioTestSuite, TestWithPatchesMixin):
    scenario = "example_1.xml"

    @property
    def submissions(self):
        """
        Submission stage contains three submissions: issue_tree, marketing_pitch and budget.
        This property simulates single submission sent by first user in group
        """
        return {
            "issue_tree": {
                "id": "issue_tree", "document_url": self.live_server_url+"/issue_tree_location",
                "document_filename": "issue_tree.doc", "modified": "2014-05-22T11:44:14Z",
                "user_details": KNOWN_USERS[1]
            }
        }

    def _assert_view_visibility(self, project_navigator, available_views, visible_view):
        """
        Checks view visibility - only `visible_view` should be displayed, other views should be hidden
        """
        hidden_views = set(available_views) - {visible_view}
        for view in hidden_views:
            try:
                self.assertFalse(project_navigator.get_view_by_type(view).is_displayed())
            except AssertionError as exception:
                logging.exception(exception)
                raise AssertionError("View {view_name} should be hidden".format(view_name=view))

        self.assertTrue(project_navigator.get_view_by_type(visible_view).is_displayed())

    def _assert_view_switching(self, project_navigator, available_views, target_view):
        """
        Checks switching views:
            * Finds view selector and clicks on it
            * Asserts that target view is now visible
            * Closes the view and asserts that default (navigation) view is displayed
        """
        project_navigator.get_view_selector_by_type(target_view).click()
        self._assert_view_visibility(project_navigator, available_views, target_view)
        view = project_navigator.get_view_by_type(target_view)
        view.close_view()
        self._assert_view_visibility(project_navigator, available_views, ViewTypes.NAVIGATION)

    def test_views(self):
        """
        Tests view rendering and switching between views.
        """
        self._prepare_page()

        available_views = {ViewTypes.NAVIGATION, ViewTypes.RESOURCES, ViewTypes.SUBMISSIONS, ViewTypes.ASK_TA}

        project_navigator = self.page.project_navigator

        self.assertEqual(len(project_navigator.views), 4)
        self.assertEqual(len(project_navigator.view_selectors), 3)  # nav view does not have selector

        view_types = set(view.type for view in project_navigator.views)
        view_selector_types = set(view.type for view in project_navigator.view_selectors)

        expected_view_types = available_views
        expected_view_selector_types = available_views - {ViewTypes.NAVIGATION}
        self.assertEqual(view_types, expected_view_types)
        self.assertEqual(view_selector_types, expected_view_selector_types)

        self._assert_view_visibility(project_navigator, available_views, ViewTypes.NAVIGATION)

        self._assert_view_switching(project_navigator, available_views, ViewTypes.RESOURCES)
        self._assert_view_switching(project_navigator, available_views, ViewTypes.SUBMISSIONS)
        self._assert_view_switching(project_navigator, available_views, ViewTypes.ASK_TA)

    def test_navigation_view(self):
        """
        Tests navigation view and stage navigation
        """
        # arrange: setting up mocks influencing stage states

        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = self.submissions
        self.make_patch(PeerReviewStage, '_pivot_feedback', mock.Mock(return_value={}))
        self.make_patch(TeamEvaluationStage, '_pivot_feedback', mock.Mock(return_value={}))

        self._prepare_page()

        nav_view = self.page.project_navigator.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
        activities_map = self.get_activities_map()

        def assert_stage(stage, activity_name, stage_type, stage_title, stage_state):
            activity_id = [
                act_id for act_id, act_name in activities_map.iteritems() if act_name == activity_name
            ][0]
            self.assertEqual(stage.activity_id, activity_id)
            # exact block ids are unknown at runtime, so using categories
            self.assertIn(stage_type.CATEGORY, stage.stage_id)
            self.assertEqual(stage.title, stage_title)
            self.assertEqual(stage.state, stage_state)

        stages = nav_view.stages
        assert_stage(stages[0], "Activity 1", BasicStage, "Overview", StageState.COMPLETED)  # marks self as complete
        assert_stage(stages[1], "Activity 1", SubmissionStage, "Upload", StageState.INCOMPLETE)  # one submission
        assert_stage(stages[2], "Activity 1", CompletionStage, "Completion", StageState.NOT_STARTED)
        assert_stage(stages[3], "Activity 2", TeamEvaluationStage, "Review Team", StageState.NOT_STARTED)
        assert_stage(stages[4], "Activity 2", PeerReviewStage, "Review Group", StageState.COMPLETED)  # no reviews
        assert_stage(stages[5], "Activity 2", EvaluationDisplayStage, "Evaluate Team Feedback", StageState.NOT_STARTED)
        assert_stage(stages[6], "Activity 2", GradeDisplayStage, "Evaluate Group Feedback", StageState.NOT_STARTED)

        # need to get this now as `navigate_to` will navigate from the page and `stage` instance will become detached
        stage_ids = [stage.stage_id for stage in nav_view.stages]
        for stage_id in stage_ids:
            stage = [st for st in nav_view.stages if st.stage_id == stage_id][0]
            activity_id = stage.activity_id
            stage.navigate_to()
            # refreshing wrappers after page reload
            self._update_after_reload()
            nav_view = self.page.project_navigator.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
            selected_stage = nav_view.selected_stage
            self.assertEqual(selected_stage.stage_id, stage_id)

            stage_content = self.page.get_activity_by_id(activity_id).get_stage_by_id(stage_id)
            self.assertTrue(stage_content.is_displayed())

    def test_resources_view(self):
        self._prepare_page()

        resoures_view = self.page.project_navigator.get_view_by_type(ViewTypes.RESOURCES, ResourcesViewElement)
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.RESOURCES).click()

        activities = resoures_view.activities
        self.assertEqual(activities[0].activity_name, "Activity 1".upper())
        self.assertEqual(activities[1].activity_name, "Activity 2".upper())

        self.assertEqual(activities[1].resources, [])

        activity1_resources = activities[0].resources
        self.assertEqual(len(activity1_resources), 4)
        self.assertEqual(activity1_resources[0].url, "http://download/file.doc")
        self.assertEqual(activity1_resources[0].title, "Issue Tree Template")

        self.assertEqual(activity1_resources[1].url, "http://download/other_file.doc")
        self.assertEqual(activity1_resources[1].title, "Instructions")

        self.assertEqual(activity1_resources[2].video_id, "0123456789abcdef")
        self.assertEqual(activity1_resources[2].title, "Video")

        self.assertEqual(activity1_resources[3].url, "http://download/mygrading.html")
        self.assertEqual(activity1_resources[3].title, "Grading Criteria")

    def test_submissions_view(self):
        issue_tree_loc = self.submissions['issue_tree']['document_url']
        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = self.submissions

        self._prepare_page()

        submissions_view = self.page.project_navigator.get_view_by_type(ViewTypes.SUBMISSIONS, SubmissionsViewElement)
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.SUBMISSIONS).click()

        activities = submissions_view.activities
        self.assertEqual(activities[0].activity_name, "Activity 1".upper())
        self.assertEqual(activities[1].activity_name, "Activity 2".upper())

        self.assertEqual(activities[1].submissions, [])

        activity1_submissions = activities[0].submissions
        issue_tree, marketing_pitch, budget = activity1_submissions

        self.assertEqual(issue_tree.title, "Issue Tree")
        self.assertEqual(issue_tree.file_location, issue_tree_loc)
        self.assertEqual(
            issue_tree.uploaded_by,
            "Uploaded by {user} on {date}".format(user=KNOWN_USERS[1].full_name, date="May 22 2014")
        )

        self.assertEqual(marketing_pitch.title, "Marketing Pitch")
        self.assertEqual(marketing_pitch.file_location, None)
        self.assertEqual(marketing_pitch.uploaded_by, '')

        self.assertEqual(budget.title, "Budget")
        self.assertEqual(budget.file_location, None)
        self.assertEqual(budget.uploaded_by, '')


@ddt.ddt
class TestProjectNavigator(BaseIntegrationTest, TestWithPatchesMixin):
    XML_TEMPLATE = textwrap.dedent("""
    <gp-v2-project>
      <gp-v2-navigator>
        {views}
      </gp-v2-navigator>
      <discussion-forum/>
    </gp-v2-project>
    """)

    def build_scenario(self, view_categories):
        views_string = "\n".join(["<{}/>".format(category) for category in view_categories])
        return self.XML_TEMPLATE.format(views=views_string)

    @ddt.data(
        (
            # test case 1 - all orderable views, correct order
            (SubmissionsViewXBlock, ResourcesViewXBlock,  AskTAViewXBlock, PrivateDiscussionViewXBlock),
            (ViewTypes.SUBMISSIONS, ViewTypes.RESOURCES, ViewTypes.ASK_TA, ViewTypes.PRIVATE_DISCUSSION)
        ),
        (
            # test case 2 - all orderable views, random order
            (AskTAViewXBlock, SubmissionsViewXBlock, PrivateDiscussionViewXBlock, ResourcesViewXBlock),
            (ViewTypes.SUBMISSIONS, ViewTypes.RESOURCES, ViewTypes.ASK_TA, ViewTypes.PRIVATE_DISCUSSION)
        ),
        (
            # test case 3 - some orderable views, correct order
            (AskTAViewXBlock, PrivateDiscussionViewXBlock),
            (ViewTypes.ASK_TA, ViewTypes.PRIVATE_DISCUSSION)
        ),
        (
            # test case 4 - some orderable views, random order
            (AskTAViewXBlock, SubmissionsViewXBlock, ResourcesViewXBlock),
            (ViewTypes.SUBMISSIONS, ViewTypes.RESOURCES, ViewTypes.ASK_TA)
        ),
    )
    @ddt.unpack
    def test_project_navigator_views_order(self, views, expected_views):
        scenario_xml = self.build_scenario([view.CATEGORY for view in views])
        self.load_scenario_xml(scenario_xml)
        scenario = self.go_to_view()
        page = GroupProjectElement(self.browser, scenario)
        project_navigator = page.project_navigator

        view_selector_types = tuple([view.type for view in project_navigator.view_selectors])
        self.assertEqual(view_selector_types, expected_views)

import mock
from selenium.webdriver.support.wait import WebDriverWait
from group_project_v2.components.project_navigator import ViewTypes
from group_project_v2.components.stage import StageState
from tests.integration.base_test import SingleScenarioTestSuite
from tests.integration.page_elements import NavigationViewElement, ResourcesViewElement, SubmissionsViewElement
from tests.utils import KNOWN_USERS


class TestProjectNavigatorViews(SingleScenarioTestSuite):
    scenario = "example_1.xml"

    def _assert_view_visibility(self, project_navigator, available_views, visible_view):
        hidden_views = set(available_views) - {visible_view}
        for view in hidden_views:
            try:
                self.assertFalse(project_navigator.get_view_by_type(view).is_displayed())
            except AssertionError as exception:
                raise AssertionError("View {view_name} should be hidden".format(view_name=view))

        self.assertTrue(project_navigator.get_view_by_type(visible_view).is_displayed())

    def _assert_view_switching(self, project_navigator, available_views, target_view):
        project_navigator.get_view_selector_by_type(target_view).click()
        self._assert_view_visibility(project_navigator, available_views, target_view)
        view = project_navigator.get_view_by_type(target_view)
        view.close_view()
        self._assert_view_visibility(project_navigator, available_views, ViewTypes.NAVIGATION)

    def test_views(self):
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
        def stage_states(course_id, activity_id, user_id, stage_id):  # pylint: disable=argument-not-used
            users_in_group, completed_users = {1, 2}, {}  # default: two users in group and no one completed
            if stage_id == "overview":
                completed_users = {1, 2}  # overview is completed
            elif stage_id == 'upload':
                completed_users = {1}  # upload is started, but incomplete
            elif stage_id == 'peer_review':
                completed_users = {3, 4}  # no intersection - not started
            elif stage_id == 'group_review':
                completed_users = {1, 2, 3, 4}  # subset - completed
            elif stage_id == 'peer_assessment':
                completed_users = {1, 3, 4}  # intersection not empty  - incomplete
            return users_in_group, completed_users

        self.project_api_mock.get_stage_state = mock.Mock(side_effect=stage_states)

        self._prepare_page()

        nav_view = self.page.project_navigator.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
        activities_map = self.get_activities_map()

        def assert_stage(stage, activity_name, stage_id, stage_title, stage_state):
            activity_id = [
                act_id for act_id, act_name in activities_map.iteritems() if act_name == activity_name
            ][0]
            self.assertEqual(stage.activity_id, activity_id)
            self.assertEqual(stage.stage_id, stage_id)
            self.assertEqual(stage.title, stage_title)
            self.assertEqual(stage.state, stage_state)

        stages = nav_view.stages
        assert_stage(stages[0], "Activity 1", "overview", "Overview", StageState.COMPLETED)
        assert_stage(stages[1], "Activity 1", "upload", "Upload", StageState.INCOMPLETE)
        assert_stage(stages[2], "Activity 2", "peer_review", "Review Team", StageState.NOT_STARTED)
        assert_stage(stages[3], "Activity 2", "group_review", "Review Group", StageState.COMPLETED)
        assert_stage(stages[4], "Activity 2", "peer_assessment", "Evaluate Team Feedback", StageState.INCOMPLETE)
        assert_stage(stages[5], "Activity 2", "group_assessment", "Evaluate Group Feedback", StageState.NOT_STARTED)

        for stage in stages:
            stage.navigate_to()
            stage_content = self.page.get_activity_by_id(stage.activity_id).get_stage_by_id(stage.stage_id)
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
        issue_tree_loc = self.live_server_url+"/issue_tree_location"
        self.project_api_mock.get_latest_workgroup_submissions_by_id = mock.Mock(return_value={
            "issue_tree": {
                "id": "issue_tree", "document_url": issue_tree_loc,
                "document_filename": "issue_tree.doc", "modified": "2014-05-22T11:44:14Z",
                "user_details": {"id": "1", "full_name": KNOWN_USERS[1]['full_name']}
            }
        })

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
            "Uploaded by {user} on {date}".format(user=KNOWN_USERS[1]['full_name'], date="May 22 2014")
        )

        self.assertEqual(marketing_pitch.title, "Marketing Pitch")
        self.assertEqual(marketing_pitch.file_location, None)
        self.assertEqual(marketing_pitch.uploaded_by, None)

        self.assertEqual(budget.title, "Budget")
        self.assertEqual(budget.file_location, None)
        self.assertEqual(budget.uploaded_by, None)

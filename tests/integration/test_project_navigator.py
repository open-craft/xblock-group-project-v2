"""
Tests for project navigator and its views
"""
import logging
import textwrap
import unittest

import ddt
import mock
from datetime import datetime

import os
from freezegun import freeze_time

from group_project_v2.project_navigator import (
    ViewTypes, ResourcesViewXBlock, SubmissionsViewXBlock, AskTAViewXBlock, PrivateDiscussionViewXBlock,
    NavigationViewXBlock)
from group_project_v2.stage import (
    BasicStage, SubmissionStage, TeamEvaluationStage, PeerReviewStage,
    EvaluationDisplayStage, GradeDisplayStage, CompletionStage
)
from group_project_v2.stage.utils import StageState
from tests.integration.base_test import SingleScenarioTestSuite, BaseIntegrationTest
from tests.integration.page_elements import (
    NavigationViewElement, ResourcesViewElement, SubmissionsViewElement, GroupProjectElement,
    AskTAViewElement, ModalDialogElement
)
from tests.utils import (
    KNOWN_USERS, TestWithPatchesMixin, switch_to_ta_grading, get_other_windows, expect_new_browser_window,
    switch_to_other_window
)


@ddt.ddt
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
                "id": "issue_tree", "document_url": self.live_server_url + "/issue_tree_location",
                "document_filename": "issue_tree.doc", "modified": "2014-05-22T11:44:14Z",
                "user_details": KNOWN_USERS[1]
            }
        }

    def _assert_view_visibility(self, project_navigator, available_views, visible_view):
        """
        Checks view visibility - only `visible_view` should be displayed, other views should be hidden
        """
        # pylint: disable=raise-missing-from
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
        self.make_patch(PeerReviewStage, 'get_review_state', mock.Mock(return_value={}))
        self.make_patch(TeamEvaluationStage, 'get_review_state', mock.Mock(return_value={}))

        self._prepare_page()

        nav_view = self.page.project_navigator.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
        activities_map = self.get_activities_map()

        def assert_stage(stage, activity_name, stage_type, stage_title, stage_state):
            activity_id = [
                act_id for act_id, act_name in activities_map.items() if act_name == activity_name
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
        assert_stage(stages[4], "Activity 2", PeerReviewStage, "Review Group", StageState.NOT_STARTED)  # no reviews
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

    @ddt.data(True, False)
    @freeze_time(datetime(2014, 5, 23))
    def test_submissions_view(self, as_ta):
        student_id = 1
        if as_ta:
            switch_to_ta_grading(self.project_api_mock)
            student_id = 100
        issue_tree_loc = self.submissions['issue_tree']['document_url']
        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = self.submissions

        self._prepare_page(student_id=student_id)

        submissions_view = self.page.project_navigator.get_view_by_type(ViewTypes.SUBMISSIONS, SubmissionsViewElement)
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.SUBMISSIONS).click()

        activities = submissions_view.activities
        self.assertEqual(activities[0].activity_name, "Activity 1".upper())
        self.assertEqual(activities[1].activity_name, "Activity 2".upper())

        self.assertEqual(activities[1].submissions, [])

        activity1_submissions = activities[0].submissions
        issue_tree, marketing_pitch, budget = activity1_submissions

        def _assert_submission(submission, title, location, uploaded_by):
            self.assertEqual(submission.title, title)
            self.assertEqual(submission.file_location, location)
            self.assertEqual(submission.uploaded_by, uploaded_by)
            self.assertTrue(submission.upload_enabled)

        issue_tree_uploaded = "Uploaded by {user} on {date}".format(user=KNOWN_USERS[1].full_name, date="May 22")
        _assert_submission(issue_tree, "Issue Tree", issue_tree_loc, issue_tree_uploaded)
        _assert_submission(marketing_pitch, "Marketing Pitch", None, '')
        _assert_submission(budget, "Budget", None, '')

    def test_download_submission(self):
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
        issue_tree, _marketing_pitch, _budget = activity1_submissions

        with expect_new_browser_window(self.browser, timeout=3):
            issue_tree.file_upload_input.click()

        new_window = get_other_windows(self.browser)[0]

        with switch_to_other_window(self.browser, new_window):
            current_url = self.browser.current_url
            self.assertEqual(current_url, issue_tree_loc)

    def test_ask_ta_view(self):
        self._prepare_page()

        ask_ta_view = self.page.project_navigator.get_view_by_type(ViewTypes.ASK_TA, AskTAViewElement)

        # open Ask TA, fill in the text, close the view and make sure it was cleared
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.ASK_TA).click()
        self.assertEqual(ask_ta_view.message, '')
        ask_ta_view.message = "Some message"
        self.assertEqual(ask_ta_view.message, "Some message")
        ask_ta_view.close_view()
        self.assertEqual(ask_ta_view.message, '')

        # open again and check if it is cleared when user opens other view
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.ASK_TA).click()
        self.assertEqual(ask_ta_view.message, '')
        ask_ta_view.message = "Some message"
        self.assertEqual(ask_ta_view.message, "Some message")
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.RESOURCES).click()
        self.assertEqual(ask_ta_view.message, '')

        # open again and submit message
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.ASK_TA).click()
        ask_ta_view.message = "Some message"
        ask_ta_view.submit_message()
        # TODO: and I have no idea yet how to check for AJAX parameters; looks like it is a work for JS test


@ddt.ddt
class TestSubmissionUpload(SingleScenarioTestSuite, TestWithPatchesMixin):
    scenario = "example_with_active_submissions.xml"

    @property
    def submissions(self):
        """
        Submission stage contains three submissions: issue_tree, marketing_pitch and budget.
        This property simulates single submission sent by first user in group
        """
        return {
            "issue_tree": {
                "id": "issue_tree", "document_url": self.live_server_url + "/issue_tree_location",
                "document_filename": "issue_tree.doc", "modified": "2014-05-22T11:44:14Z",
                "user_details": KNOWN_USERS[1]
            }
        }

    def image_path(self, image="image.png"):  # pylint: disable=no-self-use
        return os.path.join(os.path.split(__file__)[0], "../resources/", image)

    def prepare_submission(self):
        student_id = 1

        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = self.submissions

        self._prepare_page(student_id=student_id)

        submissions_view = self.page.project_navigator.get_view_by_type(ViewTypes.SUBMISSIONS, SubmissionsViewElement)
        self.page.project_navigator.get_view_selector_by_type(ViewTypes.SUBMISSIONS).click()

        activities = submissions_view.activities
        self.assertEqual(activities[0].activity_name, "Activity 1".upper())

        # Sanity check
        self.assertEqual(len(activities[0].submissions), 3)

        activity1_submissions = activities[0].submissions
        _issue_tree, marketing_pitch, _budget = activity1_submissions

        return marketing_pitch

    # TODO: figure out what's wrong with Travis
    @unittest.skipIf(os.environ.get("CI", "false") == "true", "Intermittently fails in CI")
    @ddt.data(
        "document.doc", "document.docx", "document.pdf",
        "document.ppt", "document.pptx",
        "document.xls",
        # "document.xlsx",  #django-upload-validator bug
        "image.jpeg", "image.png", "image.tiff"
    )
    def test_upload_submissions(self, document):

        marketing_pitch = self.prepare_submission()

        marketing_pitch.upload_file_and_return_modal(self.image_path(document))

        modal = ModalDialogElement(self.browser)

        self.assertEqual(modal.title, u'UPLOAD COMPLETE')
        self.assertIn(u'Your deliverable has been successfully uploaded', modal.message)

    def test_upload_submissions_restricted_file_type(self):

        marketing_pitch = self.prepare_submission()

        marketing_pitch.upload_file_and_return_modal(self.image_path("restricted_upload.gif"))

        modal = ModalDialogElement(self.browser)

        self.assertEqual(modal.title, u'ERROR')
        self.assertIn(u"File type 'image/gif' is not allowed.", modal.message)

    def test_upload_submissions_csrf(self):

        marketing_pitch = self.prepare_submission()

        with self.settings(ROOT_URLCONF='tests.integration.urlconf_overrides.csrf_failure'):
            marketing_pitch.upload_file_and_return_modal(self.image_path())

        modal = ModalDialogElement(self.browser)
        self.assertEqual(modal.title, u'ERROR')
        self.assertIn(u'An error occurred while uploading your file', modal.message)
        self.assertIn(u'Technical details: CSRF verification failed', modal.message)
        # In case message rendering text changed to escape html, this will
        # fail and notify of the error
        self.assertNotRegexpMatches(modal.message, r".*<\s*p\s*/?>")  # pylint: disable=deprecated-method

    def test_upload_submissions_plain403(self):

        marketing_pitch = self.prepare_submission()

        with self.settings(ROOT_URLCONF='tests.integration.urlconf_overrides.permission_denied'):
            marketing_pitch.upload_file_and_return_modal(self.image_path())

        modal = ModalDialogElement(self.browser)
        self.assertEqual(modal.title, u'ERROR')
        self.assertIn(u'An error occurred while uploading your file', modal.message)
        self.assertIn(u'Technical details: 403 error', modal.message)
        # In case message rendering text changed to escape html, this will
        # fail and notify of the error
        self.assertNotRegexpMatches(modal.message, r".*<\s*p\s*/?>")  # pylint: disable=deprecated-method

    def test_upload_submissions_xss_file(self):

        marketing_pitch = self.prepare_submission()

        marketing_pitch.upload_file_and_return_modal(
            self.image_path('''testdoc.<img onerror="console['log']('XSS')" src="">''')
        )

        modal = ModalDialogElement(self.browser)
        self.assertIn(u'''<img onerror="console['log']('xss')" src="">''', modal.message)
        self.assertNotIn('XSS', self.browser.get_log('browser'))


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
            (SubmissionsViewXBlock, ResourcesViewXBlock, PrivateDiscussionViewXBlock, AskTAViewXBlock),
            (ViewTypes.SUBMISSIONS, ViewTypes.RESOURCES, ViewTypes.PRIVATE_DISCUSSION, ViewTypes.ASK_TA)
        ),
        (
            # test case 2 - all orderable views, random order
            (AskTAViewXBlock, SubmissionsViewXBlock, PrivateDiscussionViewXBlock, ResourcesViewXBlock),
            (ViewTypes.SUBMISSIONS, ViewTypes.RESOURCES, ViewTypes.PRIVATE_DISCUSSION, ViewTypes.ASK_TA)
        ),
        (
            # test case 3 - some orderable views, correct order
            (PrivateDiscussionViewXBlock, AskTAViewXBlock),
            (ViewTypes.PRIVATE_DISCUSSION, ViewTypes.ASK_TA)
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

    def test_ta_views_visibility(self):
        views = (
            NavigationViewXBlock, SubmissionsViewXBlock, ResourcesViewXBlock,
            PrivateDiscussionViewXBlock, AskTAViewXBlock
        )
        switch_to_ta_grading(self.project_api_mock)
        scenario_xml = self.build_scenario([view.CATEGORY for view in views])
        self.load_scenario_xml(scenario_xml)
        scenario = self.go_to_view()
        page = GroupProjectElement(self.browser, scenario)
        project_navigator = page.project_navigator

        view_types = tuple([view.type for view in project_navigator.views])
        view_selector_types = tuple([view.type for view in project_navigator.view_selectors])

        self.assertEqual(
            view_types,
            (
                NavigationViewXBlock.type, SubmissionsViewXBlock.type, ResourcesViewXBlock.type,
                PrivateDiscussionViewXBlock.type
            )
        )
        self.assertEqual(
            view_selector_types,
            (SubmissionsViewXBlock.type, ResourcesViewXBlock.type, PrivateDiscussionViewXBlock.type)
        )

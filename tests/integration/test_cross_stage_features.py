from datetime import datetime
from freezegun import freeze_time
import mock
import pytz
from group_project_v2.project_navigator import ViewTypes
from tests.integration.base_test import SingleScenarioTestSuite
from tests.integration.page_elements import NavigationViewElement, ReviewStageElement
from tests.utils import make_submission_data, KNOWN_USERS, OTHER_GROUPS


class TestOtherGroupSubmissionLinks(SingleScenarioTestSuite):
    scenario = "submission_links_scenario.xml"

    def setUp(self):
        super(TestOtherGroupSubmissionLinks, self).setUp()
        self.project_api_mock.get_workgroups_to_review = mock.Mock(return_value=list(OTHER_GROUPS.values()))
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(return_value=[
            {"id": user.id} for user in list(KNOWN_USERS.values())
        ])

    @freeze_time(datetime(2015, 1, 1))
    def test_submission_links(self):
        other_group_submissions = {
            'issue_tree': make_submission_data(
                'http://issue_tree.csv', 'issue_tree.csv',
                datetime(2015, 1, 1, 17, 24, 15, tzinfo=pytz.UTC),
                KNOWN_USERS[1]
            ),
            'marketing_pitch': make_submission_data(
                'http://marketing_pitch.doc', 'marketing_pitch.doc',
                datetime(2015, 1, 2, 3, 4, 5, tzinfo=pytz.UTC),
                KNOWN_USERS[2]
            ),
        }
        self.project_api_mock.get_latest_workgroup_submissions_by_id = mock.Mock(return_value=other_group_submissions)
        self._prepare_page()
        nav_view = self.page.project_navigator.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
        review_stage = nav_view.get_stage_by_title("Review Group")
        review_stage.navigate_to()

        self._update_after_reload()

        stage_element = self.get_stage(self.page, stage_element_type=ReviewStageElement)

        group = stage_element.groups[0]
        group.open_group_submissions()

        self.wait_for_ajax()
        submissions_popup = stage_element.other_submission_links_popup
        self.assertIsNotNone(submissions_popup)

        stage_submissions = submissions_popup.stage_submissions
        self.assertEqual(len(stage_submissions), 2)

        stage1_submissions = stage_submissions[0]
        stage2_submissions = stage_submissions[1]
        self.assertEqual(len(stage1_submissions.uploads), 2)
        self.assertEqual(len(stage2_submissions.uploads), 1)

        issue_tree_upload = stage1_submissions.uploads[0]
        budget_upload = stage1_submissions.uploads[1]
        marketing_pitch_upload = stage2_submissions.uploads[0]

        def _assert_upload(upload, no_upload, title):
            self.assertEqual(upload.no_upload, no_upload)
            self.assertEqual(upload.title, title)
            self.assertFalse(upload.upload_data_available)

        _assert_upload(issue_tree_upload, False, "Issue Tree")
        _assert_upload(budget_upload, True, "Budget (This file has not been submitted by this group)")
        _assert_upload(marketing_pitch_upload, False, "Marketing Pitch")

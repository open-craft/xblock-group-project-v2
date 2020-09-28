import ddt
import mock

from group_project_v2.stage import SubmissionStage
from tests.unit.test_stages.base import BaseStageTest
from tests.utils import make_workgroup as mk_wg


@ddt.ddt
class TestSubmissionStage(BaseStageTest):
    block_to_test = SubmissionStage

    def _set_upload_ids(self, upload_ids):
        self.submissions_mock.return_value = [mock.Mock(upload_id=upload_id) for upload_id in upload_ids]

    def setUp(self):
        super(TestSubmissionStage, self).setUp()
        self.submissions_mock = mock.PropertyMock()
        self.make_patch(self.block_to_test, 'submissions', self.submissions_mock)

    def test_stage_is_not_graded(self):
        self.assertFalse(self.block.is_graded_stage)

    def test_stage_is_shown_on_detail_dashboard(self):
        self.assertTrue(self.block.shown_on_detail_view)

    @ddt.data(
        # no submissions at all - not started
        (['u1'], [mk_wg(1, [{'id': 1}])], {}, (set(), set())),
        # all submissions for one group with one user - user completed the stage
        (['u1'], [mk_wg(1, [{'id': 1}])], {1: ['u1']}, ({1}, set())),
        # all submissionss for one group with two users - both users completed the stage
        (['u1'], [mk_wg(1, [{'id': 1}, {'id': 2}])], {1: ['u1']}, ({1, 2}, set())),
        # some submissions for one group with one user - user partially completed the stage
        (['u1', 'u2'], [mk_wg(1, [{'id': 1}])], {1: ['u1']}, (set(), {1})),
        # some submissions for one group with two users - both users partially completed the stage
        (['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}])], {1: ['u1']}, (set(), {1, 2})),
        # two groups, some submissions for g1 - users in g1 partially completed, users in g2 not started
        (['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])], {1: ['u1']}, (set(), {1, 2})),
        # two groups, some submissions for g1 and g2 - users both in g1 and g2 partially completed
        (
                ['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])],
                {1: ['u1'], 2: ['u2']}, (set(), {1, 2, 3})
        ),
        # two groups, all submissions for g1, some for g2 - g1 users completed, g2 users partially completed
        (
                ['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])],
                {1: ['u1', 'u2'], 2: ['u2']}, ({1, 2}, {3})
        ),
        # two groups, some submissions for g1, all for g2 - g2 users completed, g1 users partially completed
        (
                ['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])],
                {1: ['u1'], 2: ['u1', 'u2']}, ({3}, {1, 2})
        ),
        # two groups, all submissions for g2, none for g1 - g2 users completed, g1 users not started
        (
                ['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])],
                {2: ['u1', 'u2']}, ({3}, set())
        ),
        # two groups, all submissions for g1 and g2 - users in g1 and g2 completed
        (
                ['u1', 'u2'], [mk_wg(1, [{'id': 1}, {'id': 2}]), mk_wg(2, [{'id': 3}])],
                {1: ['u1', 'u2'], 2: ['u1', 'u2']}, ({1, 2, 3}, set())
        ),
    )
    @ddt.unpack
    def test_get_users_completion(self, uploads, workgroups, submissions, expected_result):
        workgroup_submissions = {
            group_id: {upload_id: 'irrelevant' for upload_id in uploaded_submissions}
            for group_id, uploaded_submissions in submissions.items()
        }

        expected_completed, expected_partially_completed = expected_result
        expected_calls = [mock.call(group.id) for group in workgroups]

        def get_submissions_by_id(group_id):
            return workgroup_submissions.get(group_id, {})

        self._set_upload_ids(uploads)
        self.project_api_mock.get_latest_workgroup_submissions_by_id.side_effect = get_submissions_by_id
        completed, partially_completed = self.block.get_users_completion(workgroups, 'irrelevant')

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        self.assertEqual(
            self.project_api_mock.get_latest_workgroup_submissions_by_id.mock_calls,
            expected_calls
        )

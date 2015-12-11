from unittest import TestCase

import ddt
import mock
from xblock.field_data import DictFieldData

from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import ReducedUserDetails
from group_project_v2.stage.utils import ReviewState, StageState
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock
from tests.unit.test_stages.utils import patch_obj, USER_ID
from tests.utils import TestWithPatchesMixin, make_workgroup, make_question


class BaseStageTest(TestCase, TestWithPatchesMixin):
    block_to_test = None
    user_id = USER_ID
    workgroup_data = make_workgroup(1, [{"id": 1}, {"id": 2}, {"id": 3}])

    def setUp(self):
        self.runtime_mock = mock.Mock()
        self.activity_mock = mock.create_autospec(GroupActivityXBlock)
        self.activity_mock.content_id = '123456'
        # can't use create_autospec here, as most methods are wrapped in decorators and mock fails signature checks
        # with "Too many positional arguments" because of this
        self.project_api_mock = mock.Mock(spec_set=TypedProjectAPI)

        # pylint: disable=not-callable
        self.block = self.block_to_test(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())
        self.make_patch(self.block_to_test, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        self.make_patch(self.block_to_test, 'activity', mock.PropertyMock(return_value=self.activity_mock))
        self.real_user_id_mock = self.make_patch(self.block, 'real_user_id', mock.Mock(side_effect=lambda u_id: u_id))
        self.workgroup_mock = self.make_patch(
            self.block_to_test, 'workgroup', mock.PropertyMock(return_value=self.workgroup_data)
        )
        self.user_id_mock = self.make_patch(
            self.block_to_test, 'user_id', mock.PropertyMock(return_value=self.user_id)
        )

        self.runtime_mock.anonymous_student_id = self.user_id
        self.runtime_mock.get_real_user.side_effect = lambda uid: mock.Mock(id=uid)


@ddt.ddt
class ReviewStageBaseTest(object):
    def _make_question(self, required=False, graded=False):
        fields = {
            'grade': graded,
            'required': required
        }
        return GroupProjectReviewQuestionXBlock(self.runtime_mock, DictFieldData(fields), scope_ids=mock.Mock())

    @ddt.data(
        (False, False),
        (True, True)
    )
    @ddt.unpack
    def test_marks_visited_on_student_view(self, can_mark_complete, should_set_visited):
        can_mark_mock = mock.PropertyMock(return_value=can_mark_complete)
        self.assertFalse(self.block.visited)  # precondition check
        with patch_obj(self.block_to_test, 'can_mark_complete', can_mark_mock):
            self.block.student_view({})

            self.assertEqual(self.block.visited, should_set_visited)

    @ddt.data(
        (ReviewState.NOT_STARTED, False, StageState.NOT_STARTED),
        (ReviewState.INCOMPLETE, False, StageState.NOT_STARTED),
        (ReviewState.COMPLETED, False, StageState.NOT_STARTED),
        (ReviewState.NOT_STARTED, True, StageState.NOT_STARTED),
        (ReviewState.INCOMPLETE, True, StageState.INCOMPLETE),
        (ReviewState.COMPLETED, True, StageState.COMPLETED),
    )
    @ddt.unpack
    def test_stage_state(self, review_stage_state, visited, expected_stage_state):
        self.block.visited = visited
        patched_review_subjects = mock.PropertyMock()
        with patch_obj(self.block_to_test, 'review_status') as patched_review_status, \
                patch_obj(self.block_to_test, 'review_subjects', patched_review_subjects):
            patched_review_status.return_value = review_stage_state
            patched_review_subjects.return_value = [{'id': 1}, {'id': 2}]

            self.assertEqual(self.block.get_stage_state(), expected_stage_state)


class ReviewStageChildrenMockContextManager(object):
    def __init__(self, block, child_categories, questions):
        self._block = block
        self._child_categories = child_categories
        self._questions = questions
        self._patchers = []

    def __enter__(self):
        def _has_child_of_category(child_category):
            return child_category in self._child_categories

        has_child_mock = mock.Mock()
        patch_has_child = patch_obj(self._block, 'has_child_of_category', has_child_mock)
        has_child_mock.side_effect = _has_child_of_category
        self._patchers.append(patch_has_child)

        questions_mock = mock.PropertyMock()
        questions_mock.return_value = self._questions
        patch_questions = patch_obj(type(self._block), 'questions', questions_mock)
        self._patchers.append(patch_questions)

        for patch in self._patchers:
            patch.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch in self._patchers:
            patch.stop()

        return False


class ReviewStageUserCompletionStatsMixin(object):
    def assert_users_completion(self, expected_result, questions, target_users, workgroups=None):
        target_workgroups = workgroups if workgroups else ['irrelevant']

        expected_completed, expected_partially_completed = expected_result
        with patch_obj(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                target_workgroups,
                [ReducedUserDetails(id=uid) for uid in target_users]
            )
        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)

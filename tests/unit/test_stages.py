import itertools
from unittest import TestCase

import ddt
import mock
from xblock.field_data import DictFieldData
from xblock.validation import ValidationMessage

from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import WorkgroupDetails
from group_project_v2.stage import EvaluationDisplayStage, GradeDisplayStage, TeamEvaluationStage, PeerReviewStage
from group_project_v2.stage.utils import ReviewState, StageState
from group_project_v2.stage_components import PeerSelectorXBlock, GroupProjectReviewQuestionXBlock, GroupSelectorXBlock
from tests.utils import TestWithPatchesMixin, make_review_item


class BaseStageTest(TestCase, TestWithPatchesMixin):
    block_to_test = None
    user_id = 1
    workgroup_data = WorkgroupDetails(id=1, users=[{"id": 1}, {"id": 2}, {"id": 3}])

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
        patch_has_child = mock.patch.object(self._block, 'has_child_of_category', has_child_mock)
        has_child_mock.side_effect = _has_child_of_category
        self._patchers.append(patch_has_child)

        questions_mock = mock.PropertyMock()
        questions_mock.return_value = self._questions
        patch_questions = mock.patch.object(type(self._block), 'questions', questions_mock)
        self._patchers.append(patch_questions)

        for patch in self._patchers:
            patch.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch in self._patchers:
            patch.stop()

        return False


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
        with mock.patch.object(self.block_to_test, 'can_mark_complete', can_mark_mock):
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
        with mock.patch.object(self.block_to_test, 'review_status') as patched_review_status, \
                mock.patch.object(self.block_to_test, 'review_subjects', patched_review_subjects):
            patched_review_status.return_value = review_stage_state
            patched_review_subjects.return_value = [{'id': 1}, {'id': 2}]

            self.assertEqual(self.block.get_stage_state(), expected_stage_state)


class TestTeamEvaluationStage(ReviewStageBaseTest, BaseStageTest):
    block_to_test = TeamEvaluationStage

    def setUp(self):
        super(TestTeamEvaluationStage, self).setUp()

    def test_validation_missing_peer_selector(self):
        questions = [self._make_question()]
        categories = []
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 1)
        message = messages[0]

        self.assertEqual(message.type, ValidationMessage.ERROR)
        self.assertIn(
            u"missing required component '{ps_name}'".format(ps_name=PeerSelectorXBlock.STUDIO_LABEL),
            message.text
        )

    def test_validation_has_graded_questions(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, PeerSelectorXBlock.CATEGORY]
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 1)
        message = messages[0]

        self.assertEqual(message.type, ValidationMessage.ERROR)
        self.assertIn(u"Grade questions are not supported", message.text)

    def test_validation_passes(self):
        questions = [self._make_question()]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, PeerSelectorXBlock.CATEGORY]
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 0)


@ddt.ddt
class TestPeerReviewStage(ReviewStageBaseTest, BaseStageTest):
    block_to_test = PeerReviewStage

    def setUp(self):
        super(TestPeerReviewStage, self).setUp()

    @ddt.data(
        *itertools.product(
            (ReviewState.NOT_STARTED, ReviewState.INCOMPLETE, ReviewState.COMPLETED),
            (True, False)
        )
    )
    @ddt.unpack
    def test_stage_state_no_reviews_assigned(self, review_stage_state, visited):
        self.block.visited = visited
        patched_review_subjects = mock.PropertyMock()
        with mock.patch.object(self.block_to_test, 'review_status') as patched_review_status, \
                mock.patch.object(self.block_to_test, 'review_subjects', patched_review_subjects):
            patched_review_status.return_value = review_stage_state
            patched_review_subjects.return_value = []

            self.assertEqual(self.block.get_stage_state(), StageState.NOT_STARTED)

    def test_validation(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY]
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 1)
        message = messages[0]

        self.assertEqual(message.type, ValidationMessage.ERROR)
        self.assertIn(
            u"missing required component '{gs_name}'".format(gs_name=GroupSelectorXBlock.STUDIO_LABEL),
            message.text
        )

    def test_validation_no_graded_questions(self):
        questions = [self._make_question(graded=False)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, GroupSelectorXBlock.CATEGORY]
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 1)
        message = messages[0]

        self.assertEqual(message.type, ValidationMessage.ERROR)
        self.assertIn(u"Grade questions are required", message.text)

    def test_validation_passes(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, GroupSelectorXBlock.CATEGORY]
        with ReviewStageChildrenMockContextManager(self.block, categories, questions):
            validation = self.block.validate()

        messages = validation.messages
        self.assertEqual(len(messages), 0)


@ddt.ddt
class EvaluationStagesBaseTestMixin(object):
    def setUp(self):
        super(EvaluationStagesBaseTestMixin, self).setUp()

        self.available_now_mock = self.make_patch(
            self.block_to_test, 'available_now', mock.PropertyMock(return_value=True)
        )
        self.is_group_member_mock = self.make_patch(
            self.block_to_test, 'is_group_member', mock.PropertyMock(return_value=True)
        )

    @ddt.data(
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    )
    @ddt.unpack
    def test_can_mark_complete_base_conditions(self, available_now, is_group_member, should_proceed_calculation):
        self.available_now_mock.return_value = available_now
        self.is_group_member_mock.return_value = is_group_member
        result = self.block.can_mark_complete

        self.assert_proceeds_calculation(should_proceed_calculation)

        if not available_now or not is_group_member:
            self.assertFalse(result)

    @ddt.data(
        (False, False),
        (True, True)
    )
    @ddt.unpack
    def test_marks_complete_on_student_view(self, can_mark_complete, should_call_mark_complete):
        can_mark_mock = mock.PropertyMock(return_value=can_mark_complete)
        with mock.patch.object(self.block_to_test, 'can_mark_complete', can_mark_mock):
            self.block.student_view({})

            if should_call_mark_complete:
                self.runtime_mock.publish.assert_called_with(self.block, 'progress', {'user_id': self.block.user_id})
            else:
                self.assertFalse(self.runtime_mock.publish.called)


@ddt.ddt
class TestEvaluationDisplayStage(EvaluationStagesBaseTestMixin, BaseStageTest):
    block_to_test = EvaluationDisplayStage

    def setUp(self):
        super(TestEvaluationDisplayStage, self).setUp()

        self.team_members_mock = self.make_patch(self.block_to_test, 'team_members', mock.PropertyMock(return_value=[]))
        self.get_reviews_mock = self.make_patch(self.block, 'get_reviews')
        self.get_reviewer_ids_mock = self.make_patch(self.block, 'get_reviewer_ids')

    def assert_proceeds_calculation(self, should_perform_expensive_part):
        if should_perform_expensive_part:
            self.assertTrue(self.get_reviews_mock.called)
            self.assertTrue(self.get_reviewer_ids_mock.called)
        else:
            self.assertFalse(self.get_reviews_mock.called)
            self.assertFalse(self.get_reviewer_ids_mock.called)

    # pylint: disable=invalid-name
    def test_can_mark_complete_no_reviewers_returns_true(self):
        self.team_members_mock.return_value = []

        self.assertTrue(self.block.can_mark_complete)

    # pylint: disable=invalid-name
    def test_can_mark_complete_no_questions_returns_true(self):
        with mock.patch.object(self.block_to_test, 'required_questions') as patched_required_questions:
            patched_required_questions.return_value = []

            self.assertTrue(self.block.can_mark_complete)

    @ddt.data(
        ([10], ["q1"], [], False),
        ([10], ["q1"], [make_review_item(10, "q1")], True),
        ([10], ["q1"], [make_review_item(10, "q1"), make_review_item(10, "q2")], True),
        ([10], ["q1"], [make_review_item(11, "q1")], False),
        ([10], ["q1"], [make_review_item(10, "q2"), make_review_item(11, "q1")], False),
        ([10, 11], ["q1"], [make_review_item(10, "q1"), make_review_item(11, "q1")], True),
        ([10, 11], ["q1", "q2"], [make_review_item(10, "q1"), make_review_item(11, "q1")], False),
    )
    @ddt.unpack
    def test_can_mark_compete_suite(self, reviewers, questions, reviews, expected_result):
        self.get_reviewer_ids_mock.return_value = reviewers
        self.get_reviews_mock.return_value = reviews

        with mock.patch.object(
            self.block_to_test, 'required_questions', mock.PropertyMock()
        ) as patched_required_questions:
            patched_required_questions.return_value = questions

            self.assertEqual(self.block.can_mark_complete, expected_result)


@ddt.ddt
class TestGradeDisplayStage(EvaluationStagesBaseTestMixin, BaseStageTest):
    block_to_test = GradeDisplayStage

    def setUp(self):
        super(TestGradeDisplayStage, self).setUp()
        self.project_api_mock.get_workgroup_reviewers.return_value = [{"id": 1}]

    def assert_proceeds_calculation(self, should_perform_expensive_part):
        if should_perform_expensive_part:
            self.assertTrue(self.activity_mock.calculate_grade.called)
        else:
            self.assertFalse(self.activity_mock.calculate_grade.called)

    @ddt.data(
        (None, False),
        (10, True),
        (15, True)
    )
    @ddt.unpack
    def test_can_mark_compete_suite(self, calculate_grade_result, expected_result):
        self.activity_mock.calculate_grade.return_value = calculate_grade_result

        self.assertEqual(self.block.can_mark_complete, expected_result)

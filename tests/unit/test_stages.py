import itertools
from collections import defaultdict
from unittest import TestCase

import ddt
import mock
from xblock.field_data import DictFieldData
from xblock.validation import ValidationMessage

from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import WorkgroupDetails, ReducedUserDetails, CompletionDetails
from group_project_v2.stage import EvaluationDisplayStage, GradeDisplayStage, TeamEvaluationStage, PeerReviewStage, \
    BaseGroupActivityStage, SubmissionStage
from group_project_v2.stage.mixins import SimpleCompletionStageMixin
from group_project_v2.stage.utils import ReviewState, StageState
from group_project_v2.stage_components import PeerSelectorXBlock, GroupProjectReviewQuestionXBlock, GroupSelectorXBlock
from tests.utils import TestWithPatchesMixin, make_review_item as mri, make_question, make_workgroup as mk_wg

USER_ID = 1
OTHER_USER_ID = 2

GROUP_ID = 10
OTHER_GROUP_ID = 11


class BaseStageTest(TestCase, TestWithPatchesMixin):
    block_to_test = None
    user_id = USER_ID
    workgroup_data = mk_wg(1, [{"id": 1}, {"id": 2}, {"id": 3}])

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
class TestSubmissionStage(BaseStageTest):
    block_to_test = SubmissionStage

    def _set_upload_ids(self, upload_ids):
        self.submissions_mock.return_value = [mock.Mock(upload_id=upload_id) for upload_id in upload_ids]

    def setUp(self):
        super(TestSubmissionStage, self).setUp()
        self.submissions_mock = mock.PropertyMock()
        self.make_patch(self.block_to_test, 'submissions', self.submissions_mock)

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
            for group_id, uploaded_submissions in submissions.iteritems()
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


@ddt.ddt
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

    @ddt.data(
        ([10], ["q1"], [], ReviewState.NOT_STARTED),
        ([10], ["q1"], [mri(USER_ID, "q1", peer=10, answer='1')], ReviewState.COMPLETED),
        ([10], ["q1"], [mri(OTHER_USER_ID, "q1", peer=10, answer='1')], ReviewState.NOT_STARTED),
        (
                [10], ["q1", "q2"],
                [mri(USER_ID, "q1", peer=10, answer='1'), mri(OTHER_USER_ID, "q1", peer=10, answer='1')],
                ReviewState.INCOMPLETE
        ),
        (
                [10], ["q1"],
                [mri(USER_ID, "q1", peer=10, answer='2'), mri(USER_ID, "q2", peer=10, answer="1")],
                ReviewState.COMPLETED
        ),
        (
                [10], ["q1", "q2"],
                [mri(USER_ID, "q1", peer=10, answer='3')],
                ReviewState.INCOMPLETE
        ),
        (
                [10], ["q1"],
                [mri(USER_ID, "q2", peer=10, answer='4'), mri(USER_ID, "q1", peer=11, answer='5')],
                ReviewState.NOT_STARTED
        ),
        (
                [10, 11], ["q1"],
                [mri(USER_ID, "q1", peer=10, answer='6'), mri(USER_ID, "q1", peer=11, answer='7')],
                ReviewState.COMPLETED
        ),
        (
                [10, 11], ["q1", "q2"],
                [mri(USER_ID, "q1", peer=10, answer='7'), mri(USER_ID, "q1", peer=11, answer='8')],
                ReviewState.INCOMPLETE
        ),
    )
    @ddt.unpack
    def test_review_status(self, peers_to_review, questions, reviews, expected_result):
        self.project_api_mock.get_peer_review_items_for_group.return_value = reviews

        with mock.patch.object(self.block_to_test, 'review_subjects', mock.PropertyMock()) as patched_review_subjects, \
                mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_review_subjects.return_value = [ReducedUserDetails(id=rev_id) for rev_id in peers_to_review]
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            self.assertEqual(self.block.review_status(), expected_result)
            self.project_api_mock.get_peer_review_items_for_group.assert_called_once_with(
                self.workgroup_data.id, self.activity_mock.content_id
            )

    def _set_project_api_responses(self, workgroups, review_items):
        def workgroups_side_effect(user_id, _course_id):
            return workgroups.get(user_id, None)

        def review_items_side_effect(workgroup_id, _content_id):
            return review_items.get(workgroup_id, [])

        self.project_api_mock.get_user_workgroup_for_course.side_effect = workgroups_side_effect
        self.project_api_mock.get_peer_review_items_for_group.side_effect = review_items_side_effect

    @staticmethod
    def _parse_review_item_string(review_item_string):
        splitted = review_item_string.split(':')
        reviewer, question, peer = splitted[:3]
        if len(splitted) > 3:
            answer = splitted[3]
        else:
            answer = None
        return mri(int(reviewer), question, peer=peer, answer=answer)

    @ddt.data(
        # no reviews - not started
        ([1, 2], ["q1", "q2"], [], (set(), set())),
        # some reviews - partially completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a"], (set(), {1})),
        # all reviews - completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b"], ({1}, set())),
        # no reviews - not started
        ([1, 2, 3], ["q1", "q2"], [], (set(), set())),
        # some reviews - partially completed
        ([1, 2, 3], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b"], (set(), {1})),
        # all reviews, but some answers are None - partially completed
        ([1, 2, 3], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b", "1:q1:3", "1:q2:3:d"], (set(), {1})),
        # all reviews, but some answers are empty - partially completed
        ([1, 2, 3], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b", "1:q1:3:", "1:q2:3:d"], (set(), {1})),
        # all reviews - completed
        ([1, 2, 3], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b", "1:q1:3:c", "1:q2:3:d"], ({1}, set())),
    )
    @ddt.unpack
    def test_users_completion_single_user(self, users_in_group, questions, review_items, expected_result):
        user_id = 1
        workgroup_id = 1
        review_items = [self._parse_review_item_string(review_item_str) for review_item_str in review_items]

        self._set_project_api_responses(
            {user_id: mk_wg(workgroup_id, users=[{"id": uid} for uid in users_in_group])},
            {workgroup_id: review_items}
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=user_id)]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        self.project_api_mock.get_peer_review_items_for_group.assert_called_once_with(
            workgroup_id, self.block.activity_content_id
        )

    @ddt.data(
        # no reviews - both not started
        ([1, 2], ["q1", "q2"], [], (set(), set())),
        # u1 some reviews - u1 partially completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a"], (set(), {1})),
        # u1 all reviews - u1 completed, u2 - not started
        ([1, 2], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b"], ({1}, set())),
        # u1 some reviews, u2 some reviews - both partially completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a", "2:q1:1:b"], (set(), {1, 2})),
        # u1 all reviews, u2 some reviews - u1 completed, u2 partially completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b", "2:q1:1:c"], ({1}, {2})),
        # both all reviews - both completed
        ([1, 2], ["q1", "q2"], ["1:q1:2:a", "1:q2:2:b", "2:q1:1:c", "2:q2:1:d"], ({1, 2}, set())),
    )
    @ddt.unpack
    def test_users_completion_same_group_users(self, users_in_group, questions, review_items, expected_result):
        workgroup_id = 1
        workgroup_data = mk_wg(workgroup_id, users=[{"id": uid} for uid in users_in_group])
        review_items = [self._parse_review_item_string(review_item_str) for review_item_str in review_items]

        self._set_project_api_responses(
            {uid: workgroup_data for uid in users_in_group},
            {workgroup_id: review_items}
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=uid) for uid in users_in_group]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        self.project_api_mock.get_peer_review_items_for_group.assert_called_once_with(
            workgroup_id, self.block.activity_content_id
        )

    @ddt.data(
        # no reviews - both not started
        ([1, 3], ['q1'], {}, (set(), set())),
        # u1 some reviews - u1 partially, u4 - not started
        ([1, 4], ['q1', 'q2'], {GROUP_ID: ['1:q1:2:b']}, (set(), {1})),
        # u2 all reviews - u2 completed, u3 - not started
        ([2, 3], ['q1'], {GROUP_ID: ['2:q1:1:a']}, ({2}, set())),
        # u3 all reviews - u3 completed, u1, u2 not started
        ([1, 2, 3], ['q1'], {OTHER_GROUP_ID: ['3:q1:4:a']}, ({3}, set())),
        # u1, u2, u3 all reviews - u1, u2, u3 completed
        (
            [1, 2, 3], ['q1'],
            {GROUP_ID: ['1:q1:2:a', '2:q1:1:b'], OTHER_GROUP_ID: ['3:q1:4:c']}, ({1, 2, 3}, set())
        ),
        # u1, u2, u3 all reviews, u4 no reviews - u1, u2, u3 completed, u4 not started
        (
            [1, 2, 3, 4], ['q1'],
            {GROUP_ID: ['1:q1:2:a', '2:q1:1:b'], OTHER_GROUP_ID: ['3:q1:4:c']}, ({1, 2, 3}, set())
        ),
        # u1 all reviews, u3 some reviews - u1 completed, u3 partially completed
        (
            [1, 3], ['q1', 'q2'],
            {GROUP_ID: ['1:q1:2:a', '1:q2:2:b'], OTHER_GROUP_ID: ['3:q1:4:c']}, ({1}, {3})
        ),
    )
    @ddt.unpack
    def test_users_completion_multiple_groups(self, target_users, questions, review_items, expected_result):
        workgroups = [
            mk_wg(GROUP_ID, users=[{"id": 1}, {"id": 2}]),
            mk_wg(OTHER_GROUP_ID, users=[{"id": 3}, {"id": 4}]),
        ]
        self._set_project_api_responses(
            {1: workgroups[0], 2: workgroups[0], 3: workgroups[1], 4: workgroups[1]},
            {
                group_id: [self._parse_review_item_string(item) for item in items]
                for group_id, items in review_items.iteritems()
            }
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=uid) for uid in target_users]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        expected_calls = [
            mock.call(GROUP_ID, self.block.activity_content_id),
            mock.call(OTHER_GROUP_ID, self.block.activity_content_id)
        ]
        self.assertEqual(self.project_api_mock.get_peer_review_items_for_group.mock_calls, expected_calls)


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

    @ddt.data(
        ([GROUP_ID], ["q1"], {GROUP_ID: []}, ReviewState.NOT_STARTED),
        ([GROUP_ID], ["q1"], {GROUP_ID: [mri(USER_ID, "q1", group=GROUP_ID, answer='1')]}, ReviewState.COMPLETED),
        (
                [GROUP_ID], ["q1"],
                {GROUP_ID: [mri(OTHER_USER_ID, "q1", group=GROUP_ID, answer='1')]}, ReviewState.NOT_STARTED
        ),
        (
                [GROUP_ID], ["q1", "q2"],
                {GROUP_ID: [
                    mri(USER_ID, "q1", group=GROUP_ID, answer='1'), mri(OTHER_USER_ID, "q1", group=GROUP_ID, answer='1')
                ]},
                ReviewState.INCOMPLETE
        ),
        (
                [GROUP_ID], ["q1"],
                {GROUP_ID: [
                    mri(USER_ID, "q1", group=GROUP_ID, answer='2'), mri(USER_ID, "q2", group=GROUP_ID, answer="1")
                ]},
                ReviewState.COMPLETED
        ),
        (
                [GROUP_ID], ["q1", "q2"],
                {GROUP_ID: [mri(USER_ID, "q1", group=GROUP_ID, answer='3')]},
                ReviewState.INCOMPLETE
        ),
        (
                [GROUP_ID], ["q1"],
                {GROUP_ID: [
                    mri(USER_ID, "q2", group=GROUP_ID, answer='4'), mri(USER_ID, "q1", group=OTHER_GROUP_ID, answer='5')
                ]},
                ReviewState.NOT_STARTED
        ),
        (
                [GROUP_ID, OTHER_GROUP_ID], ["q1"],
                {
                    GROUP_ID: [mri(USER_ID, "q1", group=GROUP_ID, answer='6')],
                    OTHER_GROUP_ID: [mri(USER_ID, "q1", group=OTHER_GROUP_ID, answer='7')]
                },
                ReviewState.COMPLETED
        ),
        (
                [GROUP_ID, OTHER_GROUP_ID], ["q1", "q2"],
                {
                    GROUP_ID: [mri(USER_ID, "q1", group=GROUP_ID, answer='7')],
                    OTHER_GROUP_ID: [mri(USER_ID, "q1", group=OTHER_GROUP_ID, answer='8')]
                },
                ReviewState.INCOMPLETE
        ),
        (
                [GROUP_ID, OTHER_GROUP_ID], ["q1", "q2"],
                {
                    GROUP_ID: [
                        mri(USER_ID, "q1", group=GROUP_ID, answer='7'), mri(USER_ID, "q2", group=GROUP_ID, answer='7')
                    ],
                    OTHER_GROUP_ID: [
                        mri(USER_ID, "q1", group=OTHER_GROUP_ID, answer='8'),
                        mri(USER_ID, "q2", group=GROUP_ID, answer='7')
                    ]
                },
                ReviewState.INCOMPLETE
        ),
    )
    @ddt.unpack
    def test_review_status(self, groups, questions, reviews, expected_result):
        def get_reviews(group_id, _component_id):
            return reviews.get(group_id, [])

        expected_calls = [
            mock.call(group_id, self.block.activity_content_id)
            for group_id in groups
        ]
        self.project_api_mock.get_workgroup_review_items_for_group.side_effect = get_reviews

        with mock.patch.object(self.block_to_test, 'review_subjects', mock.PropertyMock()) as patched_review_subjects, \
                mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_review_subjects.return_value = [WorkgroupDetails(id=rev_id) for rev_id in groups]
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            self.assertEqual(self.block.review_status(), expected_result)

        self.assertEqual(self.project_api_mock.get_workgroup_review_items_for_group.mock_calls, expected_calls)

    def _set_project_api_responses(self, workgroups, review_items):
        def workgroups_side_effect(user_id, _course_id, _content_id):
            return workgroups.get(user_id, None)

        def review_items_side_effect(workgroup_id, _content_id):
            return review_items.get(workgroup_id, [])

        self.project_api_mock.get_workgroups_to_review.side_effect = workgroups_side_effect
        self.project_api_mock.get_workgroup_review_items_for_group.side_effect = review_items_side_effect

    @staticmethod
    def _parse_review_item_string(review_item_string):
        splitted = review_item_string.split(':')
        reviewer, question, group = splitted[:3]
        if len(splitted) > 3:
            answer = splitted[3]
        else:
            answer = None
        return mri(int(reviewer), question, group=group, answer=answer)

    @ddt.data(
        # no reviews - not started
        ([GROUP_ID], ["q1"], [], (set(), set())),
        # some reviews - partially completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a"], (set(), {1})),
        # some reviews - partially completed; other reviewers reviews doe not affect the state
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "2:q1:10:a", "2:q2:10:a"], (set(), {1})),
        # all reviews - completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "1:q2:10:a"], ({1}, set())),
        # no reviews - not started
        ([GROUP_ID, OTHER_GROUP_ID], ["q1", "q2"], [], (set(), set())),
        # some reviews - partially completed
        ([GROUP_ID, OTHER_GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "1:q2:10:b"], (set(), {1})),
        # all reviews, but some answers are None - partially completed
        ([GROUP_ID, OTHER_GROUP_ID], ["q1"], ["1:q1:10:a", "1:q1:11"], (set(), {1})),
        # all reviews, but some answers are empty - partially completed
        ([GROUP_ID, OTHER_GROUP_ID], ["q1"], ["1:q1:10:a", "1:q1:11:"], (set(), {1})),
        # all reviews - completed
        ([GROUP_ID, OTHER_GROUP_ID], ["q1"], ["1:q1:10:a", "1:q1:11:b"], ({1}, set())),
    )
    @ddt.unpack
    def test_users_completion_single_user(self, groups_to_review, questions, review_items, expected_result):
        user_id = 1
        review_items = [self._parse_review_item_string(review_item_str) for review_item_str in review_items]

        self._set_project_api_responses(
            {user_id: [mk_wg(group_id) for group_id in groups_to_review]},
            {GROUP_ID: review_items}
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=user_id)]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        expected_calls = [mock.call(group_id, self.block.activity_content_id) for group_id in groups_to_review]
        self.assertEqual(self.project_api_mock.get_workgroup_review_items_for_group.mock_calls, expected_calls)

    @ddt.data(
        # no reviews - both not started
        ([GROUP_ID], ["q1", "q2"], [], (set(), set())),
        # u1 some reviews - u1 partially completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a"], (set(), {1})),
        # u1 all reviews - u1 completed, u2 - not started
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "1:q2:10:b"], ({1}, set())),
        # u1 some reviews, u2 some reviews - both partially completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "2:q1:10:b"], (set(), {1, 2})),
        # u1 all reviews, u2 some reviews - u1 completed, u2 partially completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "1:q2:10:b", "2:q1:10:c"], ({1}, {2})),
        # both all reviews - both completed
        ([GROUP_ID], ["q1", "q2"], ["1:q1:10:a", "1:q2:10:b", "2:q1:10:c", "2:q2:10:d"], ({1, 2}, set())),
    )
    @ddt.unpack
    def test_users_completion_same_groups(self, groups_to_review, questions, review_items, expected_result):
        target_users = [1, 2]
        review_items = [self._parse_review_item_string(review_item_str) for review_item_str in review_items]

        self._set_project_api_responses(
            {user_id: [mk_wg(group_id) for group_id in groups_to_review] for user_id in target_users},
            {GROUP_ID: review_items}
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=uid) for uid in target_users]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(
            GROUP_ID, self.block.activity_content_id
        )

    @ddt.data(
        # no reviews - both not started
        ([1, 3], {GROUP_ID: [1, 3]}, ['q1'], {}, (set(), set())),
        # u1 some reviews - u1 partially, u4 - not started
        ([1, 4], {GROUP_ID: [1, 4]}, ['q1', 'q2'], {GROUP_ID: ['1:q1:10:b']}, (set(), {1})),
        # u2 all reviews - u2 completed, u3 - not started
        ([2, 3], {GROUP_ID: [2, 3]}, ['q1'], {GROUP_ID: ['2:q1:10:a']}, ({2}, set())),
        # u3 all reviews - u3 completed, u1, u2 not started
        ([1, 2, 3], {OTHER_GROUP_ID: [1, 2, 3]}, ['q1'], {OTHER_GROUP_ID: ['3:q1:11:a']}, ({3}, set())),
        # u1, u2, u3 all reviews - u1, u2, u3 completed
        (
            [1, 2, 3], {GROUP_ID: [1, 2], OTHER_GROUP_ID: [3]}, ['q1'],
            {GROUP_ID: ['1:q1:10:a', '2:q1:10:b'], OTHER_GROUP_ID: ['3:q1:11:c']}, ({1, 2, 3}, set())
        ),
        # u1, u2, u3 all reviews, u4 no reviews - u1, u2, u3 completed, u4 not started
        (
            [1, 2, 3, 4], {GROUP_ID: [1, 2], OTHER_GROUP_ID: [3, 4]}, ['q1'],
            {GROUP_ID: ['1:q1:10:a', '2:q1:10:b'], OTHER_GROUP_ID: ['3:q1:11:c']}, ({1, 2, 3}, set())
        ),
        # u1 all reviews, u3 some reviews - u1 completed, u3 partially completed
        (
            [1, 3], {GROUP_ID: [1, 3], OTHER_GROUP_ID: [3]}, ['q1', 'q2'],
            {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '3:q1:10:c', '3:q2:10:d'], OTHER_GROUP_ID: ['3:q1:11:e']}, ({1}, {3})
        ),
        # u1 all reviews, u3 some reviews - u1 completed, u3 partially completed
        (
            [1, 3], {GROUP_ID: [1, 3], OTHER_GROUP_ID: [3]}, ['q1', 'q2'],
            {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '3:q1:10:c'], OTHER_GROUP_ID: ['3:q1:11:e', '3:q2:11:d']}, ({1}, {3})
        ),
    )
    @ddt.unpack
    # pylint:disable=too-many-locals
    def test_users_completion_multiple_groups(
            self, target_users, group_reviewers, questions, review_items, expected_result
    ):
        groups_to_review = defaultdict(list)
        for group_id, reviewers in group_reviewers.iteritems():
            for reviewer in reviewers:
                groups_to_review[reviewer].append(mk_wg(group_id))

        self._set_project_api_responses(
            groups_to_review,
            {
                group_id: [self._parse_review_item_string(item) for item in items]
                for group_id, items in review_items.iteritems()
            }
        )

        expected_completed, expected_partially_completed = expected_result

        with mock.patch.object(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            completed, partially_completed = self.block.get_users_completion(
                ['irrelevant'],
                [ReducedUserDetails(id=uid) for uid in target_users]
            )

        self.assertEqual(completed, expected_completed)
        self.assertEqual(partially_completed, expected_partially_completed)
        # checks if caching is ok
        expected_calls = [
            mock.call(group_id, self.block.activity_content_id) for group_id in group_reviewers.keys()
        ]
        self.assertEqual(self.project_api_mock.get_workgroup_review_items_for_group.mock_calls, expected_calls)


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

    def test_can_mark_complete_no_reviewers_returns_true(self):
        self.team_members_mock.return_value = []

        self.assertTrue(self.block.can_mark_complete)

    def test_can_mark_complete_no_questions_returns_true(self):
        with mock.patch.object(self.block_to_test, 'required_questions') as patched_required_questions:
            patched_required_questions.return_value = []

            self.assertTrue(self.block.can_mark_complete)

    @ddt.data(
        ([10], ["q1"], [], False),
        ([10], ["q1"], [mri(10, "q1")], True),
        ([10], ["q1"], [mri(10, "q1"), mri(10, "q2")], True),
        ([10], ["q1"], [mri(11, "q1")], False),
        ([10], ["q1"], [mri(10, "q2"), mri(11, "q1")], False),
        ([10, 11], ["q1"], [mri(10, "q1"), mri(11, "q1")], True),
        ([10, 11], ["q1", "q2"], [mri(10, "q1"), mri(11, "q1")], False),
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


@ddt.ddt
class TestSimpleCompletionStageMixin(BaseStageTest):
    class SimpleCompletionGuineaPig(SimpleCompletionStageMixin, BaseGroupActivityStage):
        pass

    block_to_test = SimpleCompletionGuineaPig

    @ddt.data(
        ({1}, {1}),
        (set(), set()),
        ({1, 2, 3, 4}, {1, 2, 3, 4}),
        ({1, 4, 11, 92}, {1, 4, 11, 92}),
    )
    @ddt.unpack
    def test_get_users_completion(self, completed_users, expected_completed_users):
        self.project_api_mock.get_completions_by_content_id.return_value = [
            CompletionDetails(user_id=uid) for uid in completed_users
        ]

        completed, partially = self.block.get_users_completion('irrelevant', 'irrelevant')
        self.assertEqual(completed, expected_completed_users)
        self.assertEqual(partially, set())
        self.project_api_mock.get_completions_by_content_id.assert_called_once_with(
            self.block.course_id, self.block.content_id
        )

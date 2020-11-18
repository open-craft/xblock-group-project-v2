import itertools
from collections import defaultdict

import ddt
import mock
from xblock.validation import ValidationMessage

from group_project_v2.project_api.dtos import WorkgroupDetails
from group_project_v2.stage import PeerReviewStage
from group_project_v2.stage.utils import ReviewState, StageState
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock, GroupSelectorXBlock
from tests.unit.test_stages.base import BaseStageTest, ReviewStageBaseTest, ReviewStageUserCompletionStatsMixin
from tests.unit.test_stages.utils import GROUP_ID, OTHER_GROUP_ID, OTHER_USER_ID, USER_ID, patch_obj
from tests.utils import make_question
from tests.utils import make_review_item as mri
from tests.utils import make_workgroup as mk_wg


@ddt.ddt
class TestPeerReviewStage(ReviewStageBaseTest, BaseStageTest):
    block_to_test = PeerReviewStage

    def test_stage_is_graded(self):
        self.assertTrue(self.block.is_graded_stage)

    def test_stage_is_shown_on_detail_dashboard(self):
        self.assertTrue(self.block.shown_on_detail_view)

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
        with patch_obj(self.block_to_test, 'review_status') as patched_review_status, \
                patch_obj(self.block_to_test, 'review_subjects', patched_review_subjects):
            patched_review_status.return_value = review_stage_state
            patched_review_subjects.return_value = []

            self.assertEqual(self.block.get_stage_state(), StageState.NOT_STARTED)

    @ddt.data(True, False)
    def test_can_mark_complete_admin_grader(self, available_now):
        with patch_obj(self.block_to_test, 'is_admin_grader', mock.PropertyMock(return_value=True)), \
                patch_obj(self.block_to_test, 'available_now', mock.PropertyMock(return_value=available_now)):
            self.assertEqual(self.block.can_mark_complete, True)

    def test_validation(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY]
        expected_message = ValidationMessage(
            ValidationMessage.ERROR,
            u"missing required component '{gs_name}'".format(gs_name=GroupSelectorXBlock.STUDIO_LABEL),
        )
        self.validate_and_check_message(categories, questions, expected_message)

    def test_validation_no_graded_questions(self):
        questions = [self._make_question(graded=False)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, GroupSelectorXBlock.CATEGORY]
        expected_message = ValidationMessage(ValidationMessage.ERROR, u"Grade questions are required")
        self.validate_and_check_message(categories, questions, expected_message)

    def test_validation_passes(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, GroupSelectorXBlock.CATEGORY]
        self.validate_and_check_message(categories, questions)


@ddt.ddt
class TestPeerReviewStageReviewStatus(ReviewStageBaseTest, ReviewStageUserCompletionStatsMixin, BaseStageTest):
    block_to_test = PeerReviewStage

    def setUp(self):
        super(TestPeerReviewStageReviewStatus, self).setUp()
        self.activity_mock.is_ta_graded = False

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

        with patch_obj(self.block_to_test, 'review_subjects', mock.PropertyMock()) as patched_review_subjects, \
                patch_obj(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
            patched_review_subjects.return_value = [WorkgroupDetails(id=rev_id) for rev_id in groups]
            patched_questions.return_value = [make_question(q_id, 'irrelevant') for q_id in questions]

            self.assertEqual(self.block.review_status(), expected_result)

        self.assertEqual(self.project_api_mock.get_workgroup_review_items_for_group.mock_calls, expected_calls)

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

        self.assert_users_completion(expected_result, questions, [user_id])

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

        self.assert_users_completion(expected_result, questions, target_users)
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
        for group_id, reviewers in group_reviewers.items():
            for reviewer in reviewers:
                groups_to_review[reviewer].append(mk_wg(group_id))

        self._set_project_api_responses(
            groups_to_review,
            {
                group_id: [self._parse_review_item_string(item) for item in items]
                for group_id, items in review_items.items()
            }
        )

        self.assert_users_completion(expected_result, questions, target_users)
        # checks if caching is ok
        expected_calls = [
            mock.call(group_id, self.block.activity_content_id) for group_id in list(group_reviewers.keys())
        ]
        self.assertEqual(self.project_api_mock.get_workgroup_review_items_for_group.mock_calls, expected_calls)

    @ddt.data(
        # no reviewers - not started
        ([], ['q1'], {}, StageState.NOT_STARTED),
        # no reviews - not started
        ([1], ['q1'], {}, StageState.NOT_STARTED),
        # complete review for one group - completed
        ([1], ['q1'], {GROUP_ID: ['1:q1:10:a']}, StageState.COMPLETED),
        # partial review for one group - partially complete
        ([1], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a']}, StageState.INCOMPLETE),
        # complete review for one group with multiple questions - completed
        ([1], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b']}, StageState.COMPLETED),
        # multiple reviewers - no reviews - not started
        ([1, 2], ['q1'], {}, StageState.NOT_STARTED),
        # multiple reviewers - one partial, other not started - partially complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a']}, StageState.INCOMPLETE),
        # multiple reviewers - both partial - partially complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '2:q2:10:b']}, StageState.INCOMPLETE),
        # multiple reviewers - one complete, one partial - partially complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '2:q2:10:b']}, StageState.INCOMPLETE),
        # multiple reviewers - both complete - complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '2:q1:10:c', '2:q2:10:d']}, StageState.COMPLETED),
    )
    @ddt.unpack
    def test_get_external_group_status(self, reviewers, questions, review_items, expected_result):
        group = mk_wg(GROUP_ID, [{"id": 1}])
        self.project_api_mock.get_workgroup_reviewers.return_value = [{'id': user_id} for user_id in reviewers]

        self._set_project_api_responses(
            group,
            {
                group.id: [self._parse_review_item_string(item) for item in items]
                for group_id, items in review_items.items()
            }
        )

        self.assert_group_completion(group, questions, expected_result)
        self.project_api_mock.get_workgroup_reviewers.assert_called_once_with(group.id, self.block.activity_content_id)

    @ddt.data(
        # no ta reviewers - not started
        ([], ['q1'], {}, StageState.NOT_STARTED),
        # no reviews - not started
        ([1], ['q1'], {}, StageState.NOT_STARTED),
        # complete review for one group - completed
        ([1], ['q1'], {GROUP_ID: ['1:q1:10:a']}, StageState.COMPLETED),
        # partial review for one group - partially complete
        ([1], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a']}, StageState.INCOMPLETE),
        # complete review for one group with multiple questions - completed
        ([1], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b']}, StageState.COMPLETED),
        # multiple TAs - no reviews - not started
        ([1, 2], ['q1'], {}, StageState.NOT_STARTED),
        # multiple TAs - one partial, other not started - partially complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a']}, StageState.INCOMPLETE),
        # multiple TAs - both partial - partially complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '2:q2:10:b']}, StageState.INCOMPLETE),
        # multiple TAs - one complete, other partial - complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '2:q2:10:c']}, StageState.COMPLETED),
        # multiple reviewers - both complete - complete
        ([1, 2], ['q1', 'q2'], {GROUP_ID: ['1:q1:10:a', '1:q2:10:b', '2:q2:10:c', '2:q2:10:d']}, StageState.COMPLETED),
    )
    @ddt.unpack
    def test_ta_get_external_group_status(self, ta_reviewers, questions, review_items, expected_result):
        group_to_review = mk_wg(GROUP_ID, [{"id": 1}])
        self.activity_mock.is_ta_graded = True

        self._set_project_api_responses(
            group_to_review,
            {
                group_to_review.id: [self._parse_review_item_string(item) for item in items]
                for group_id, items in review_items.items()
            }
        )

        with patch_obj(self.block, 'is_user_ta') as patched_outsider_allowed:
            patched_outsider_allowed.side_effect = lambda user_id, _course_id: user_id in ta_reviewers

            self.assert_group_completion(group_to_review, questions, expected_result)

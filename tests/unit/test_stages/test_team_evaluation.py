import ddt
import mock
from xblock.validation import ValidationMessage

from group_project_v2.project_api.dtos import ReducedUserDetails
from group_project_v2.stage import TeamEvaluationStage
from group_project_v2.stage.utils import ReviewState
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock, PeerSelectorXBlock
from tests.unit.test_stages.base import BaseStageTest, ReviewStageBaseTest, ReviewStageUserCompletionStatsMixin
from tests.unit.test_stages.utils import GROUP_ID, OTHER_GROUP_ID, OTHER_USER_ID, USER_ID, patch_obj
from tests.utils import make_question
from tests.utils import make_review_item as mri
from tests.utils import make_workgroup as mk_wg


@ddt.ddt
class TestTeamEvaluationStage(ReviewStageBaseTest, BaseStageTest):
    block_to_test = TeamEvaluationStage

    def test_validation_missing_peer_selector(self):
        questions = [self._make_question()]
        categories = []
        expected_message = ValidationMessage(
            ValidationMessage.ERROR,
            u"missing required component '{ps_name}'".format(ps_name=PeerSelectorXBlock.STUDIO_LABEL)
        )
        self.validate_and_check_message(categories, questions, expected_message)

    def test_validation_has_graded_questions(self):
        questions = [self._make_question(graded=True)]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, PeerSelectorXBlock.CATEGORY]
        expected_message = ValidationMessage(ValidationMessage.ERROR, u"Graded questions are not supported")
        self.validate_and_check_message(categories, questions, expected_message)

    def test_validation_passes(self):
        questions = [self._make_question()]
        categories = [GroupProjectReviewQuestionXBlock.CATEGORY, PeerSelectorXBlock.CATEGORY]
        self.validate_and_check_message(categories, questions, None)


@ddt.ddt
class TestTeamEvaluationStageStageStatus(ReviewStageUserCompletionStatsMixin, BaseStageTest):
    block_to_test = TeamEvaluationStage

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

        with patch_obj(self.block_to_test, 'review_subjects', mock.PropertyMock()) as patched_review_subjects, \
                patch_obj(self.block_to_test, 'required_questions', mock.PropertyMock()) as patched_questions:
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

        self.assert_users_completion(expected_result, questions, [user_id])

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

        self.assert_users_completion(expected_result, questions, users_in_group)
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
                for group_id, items in review_items.items()
            }
        )

        self.assert_users_completion(expected_result, questions, target_users)

        # checks if caching is ok
        expected_calls = [
            mock.call(GROUP_ID, self.block.activity_content_id),
            mock.call(OTHER_GROUP_ID, self.block.activity_content_id)
        ]
        self.assertEqual(self.project_api_mock.get_peer_review_items_for_group.mock_calls, expected_calls)

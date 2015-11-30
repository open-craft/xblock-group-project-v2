from unittest import TestCase

import ddt
import mock
from xblock.runtime import Runtime
from xblock.field_data import DictFieldData

from group_project_v2.group_project import GroupActivityXBlock, GroupProjectXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import ProjectDetails, WorkgroupDetails
from group_project_v2.stage import BaseGroupActivityStage, TeamEvaluationStage, PeerReviewStage
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock
from tests.utils import TestWithPatchesMixin, make_review_item


def _make_question(question_id):
    question_mock = mock.create_autospec(spec=GroupProjectReviewQuestionXBlock)
    question_mock.question_id = question_id
    return question_mock


def _make_reviews(reviews):
    return [
        make_review_item(reviewer, question, answer=answer)
        for reviewer, question, answer in reviews
    ]


def _make_workgroup(user_ids):
    return WorkgroupDetails(users=[{'id': user_id} for user_id in user_ids])


@ddt.ddt
class TestGroupProjectXBlock(TestWithPatchesMixin, TestCase):
    def setUp(self):
        super(TestGroupProjectXBlock, self).setUp()
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.project_api_mock = mock.Mock(spec=TypedProjectAPI)
        self.block = GroupProjectXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())
        self.make_patch(GroupProjectXBlock, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))

    @ddt.data(
        (1, 'content1', 'course1'),
        (2, 'content2', 'course2')
    )
    @ddt.unpack
    def test_project_id(self, project_id, content_id, course_id):
        project_details = ProjectDetails(id=project_id, content_id=content_id, course_id=course_id)
        self.project_api_mock.get_project_by_content_id.return_value = project_details

        self.assertEqual(self.block.project_details, project_details)
        self.project_api_mock.get_project_by_content_id.assert_called_once_with(
            self.block.course_id, self.block.content_id
        )


@ddt.ddt
class TestGroupActivityXBlock(TestWithPatchesMixin, TestCase):
    def setUp(self):
        super(TestGroupActivityXBlock, self).setUp()
        self.project_api_mock = mock.Mock(spec=TypedProjectAPI)
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.block = GroupActivityXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())
        self.make_patch(GroupActivityXBlock, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))

        self.group_project_mock = mock.Mock(spec=GroupProjectXBlock)
        self.group_project_mock.content_id = 'test_project_content_id'
        self.make_patch(GroupActivityXBlock, 'project', mock.PropertyMock(return_value=self.group_project_mock))

    @ddt.data(
        ([], []),
        (['q1', 'q2', 'q3'], ['q1', 'q2'], ['q3']),
        (['q8', 'q12', 'q22', 'q54'], ['q8'], ['q12', 'q22'], ['q54'])
    )
    @ddt.unpack
    def test_questions_property(self, expected_result, *stage_questions):
        stages = []
        for questions in stage_questions:
            stage_mock = mock.create_autospec(BaseGroupActivityStage)
            stage_mock.questions = questions
            stages.append(stage_mock)

        with mock.patch.object(self.block.__class__, 'stages', mock.PropertyMock()) as stages_mock:
            stages_mock.return_value = stages
            self.assertEqual(self.block.questions, expected_result)

    @ddt.data(
        ([], []),
        (['q1', 'q2', 'q3'], ['q1', 'q2'], ['q3']),
        (['q8', 'q12', 'q22', 'q54'], ['q8'], ['q12', 'q22'], ['q54'])
    )
    @ddt.unpack
    def test_grade_questions_property(self, expected_result, *stage_questions):
        stages = []
        for questions in stage_questions:
            stage_mock = mock.create_autospec(BaseGroupActivityStage)
            stage_mock.grade_questions = questions
            stages.append(stage_mock)

        with mock.patch.object(self.block.__class__, 'stages', mock.PropertyMock()) as stages_mock:
            stages_mock.return_value = stages
            self.assertEqual(self.block.grade_questions, expected_result)

    @ddt.data(
        ([], []),
        (['q1', 'q2', 'q3'], ['q1', 'q2'], ['q3']),
        (['q8', 'q12', 'q22', 'q54'], ['q8'], ['q12', 'q22'], ['q54'])
    )
    @ddt.unpack
    def test_team_evaluation_questions(self, expected_result, *stage_questions):
        stages = []
        for questions in stage_questions:
            stage_mock = mock.create_autospec(TeamEvaluationStage)
            stage_mock.questions = questions
            stages.append(stage_mock)

        with mock.patch.object(self.block, 'get_children_by_category', mock.Mock()) as get_stages:
            get_stages.return_value = stages

            result = self.block.team_evaluation_questions
            self.assertEqual(result, expected_result)

            get_stages.assert_called_with(TeamEvaluationStage.CATEGORY)

    @ddt.data(
        ([], []),
        (['q1', 'q2', 'q3'], ['q1', 'q2'], ['q3']),
        (['q8', 'q12', 'q22', 'q54'], ['q8'], ['q12', 'q22'], ['q54'])
    )
    @ddt.unpack
    def test_peer_grade_questions(self, expected_result, *stage_questions):
        stages = []
        for questions in stage_questions:
            stage_mock = mock.create_autospec(PeerReviewStage)
            stage_mock.questions = questions
            stages.append(stage_mock)

        with mock.patch.object(self.block, 'get_children_by_category', mock.Mock()) as get_stages:
            get_stages.return_value = stages

            result = self.block.peer_review_questions
            self.assertEqual(result, expected_result)

            get_stages.assert_called_with(PeerReviewStage.CATEGORY)

    @ddt.data(
        (1, 'content1', 'course1'),
        (2, 'content2', 'course2')
    )
    @ddt.unpack
    def test_project_id(self, project_id, content_id, course_id):
        project_details = ProjectDetails(id=project_id, content_id=content_id, course_id=course_id)
        self.group_project_mock.project_details = project_details

        self.assertEqual(self.block.project_details, project_details)


@ddt.ddt
class TestCalculateGradeGroupActivityXBlock(TestWithPatchesMixin, TestCase):
    def setUp(self):
        self.project_api_mock = mock.PropertyMock()
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.grade_questions_mock = mock.PropertyMock()
        self.block = GroupActivityXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())

        self.make_patch(GroupActivityXBlock, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        self.grade_questions_mock = self.make_patch(GroupActivityXBlock, 'grade_questions', mock.PropertyMock())
        self.real_user_id_mock = self.make_patch(self.block, 'real_user_id')
        self.real_user_id_mock.side_effect = lambda u_id: u_id

    @ddt.data(
        (1, ["q1"], [1], [], None),
        (2, ["q1", "q2"], [1], [], None),
        (3, ["q1"], [1, 2], [], None),
        (4, ["q1"], [1], [(1, "q1", 100)], 100),
        (5, ["q1", "q2"], [1], [(1, "q1", 20), (1, "q2", 30)], 25),
        (6, ["q1", "q2"], [1], [(1, "q1", 1), (1, "q2", 2)], round((1.0+2.0)/2.0)),  # rounding
        (7, ["q1", "q2"], [1, 2], [(1, "q1", 1), (1, "q2", 2)], None),
        (8, ["q1", "q2"], [1, 2], [(1, "q1", 1), (1, "q2", 2), (2, "q2", 0)], None),
        (9, ["q1", "q2"], [1, 2], [(1, "q1", 10), (1, "q2", 20), (2, "q1", 30), (2, "q2", 60)], 30.0),
    )
    @ddt.unpack
    def test_calculate_grade(self, group_id, question_ids, reviewer_ids, reviews, expected_grade):
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(
            return_value=[{"id": rew_id} for rew_id in reviewer_ids]
        )
        self.project_api_mock.get_workgroup_review_items_for_group = mock.Mock(return_value=_make_reviews(reviews))

        self.grade_questions_mock.return_value = [_make_question(question_id) for question_id in question_ids]

        grade = self.block.calculate_grade(group_id)
        self.assertEqual(grade, expected_grade)
        self.project_api_mock.get_workgroup_reviewers.assert_called_once_with(group_id, self.block.content_id)
        self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(
            group_id, self.block.content_id
        )

    # pylint: disable=too-many-arguments
    @ddt.data(
        (0, ["q1"], [], [], [], None),  # no reviews at all
        (1, ["q1"], [], [], [(10, "q1", 15)], 15),  # one admin review
        (1, ["q1"], [], [], [(10, "q1", 15), (20, "q1", 75)], 45),  # two admin reviews for same question - mean of two
        (2, ["q1", "q2"], [], [], [(10, "q1", 15)], None),  # incomplete admin review is ignored
        (2, ["q1", "q2"], [], [], [(10, "q1", 15), (10, "q2", 25)], 20),  # two questions
        (2, ["q1", "q2"], [], [], [(10, "q1", 15), (10, "q2", 25), (20, "q2", 100)], 20),  # incomplete second review
        (2, ["q1"], [1], [(1, "q1", 100)], [(10, "q1", 15)], 100),  # user reviews takes precedence
        (2, ["q1"], [1, 2], [(1, "q1", 100)], [(10, "q1", 20)], 60),  # if a user failed to review admin grade used
        (2, ["q1"], [1, 2, 3], [(1, "q1", 100)], [(10, "q1", 25)], 50),  # if a user failed to review admin grade used
    )
    @ddt.unpack
    def test_calculate_grade_with_admins(
        self, group_id, question_ids, reviewer_ids, reviews, admin_reviews, expected_grade
    ):
        self.project_api_mock.get_workgroup_reviewers = mock.Mock(
            return_value=[{"id": rew_id} for rew_id in reviewer_ids]
        )
        self.project_api_mock.get_workgroup_review_items_for_group = mock.Mock(
            return_value=_make_reviews(reviews)+_make_reviews(admin_reviews)
        )

        self.grade_questions_mock.return_value = [_make_question(question_id) for question_id in question_ids]
        self.real_user_id_mock.side_effect = lambda u_id: u_id

        grade = self.block.calculate_grade(group_id)
        self.assertEqual(grade, expected_grade)
        self.project_api_mock.get_workgroup_reviewers.assert_called_once_with(group_id, self.block.content_id)
        self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(
            group_id, self.block.content_id
        )


@ddt.ddt
class TestEventsAndCompletionGroupActivityXBlock(TestWithPatchesMixin, TestCase):
    STANDARD_DATA = (
        (1, [], 100),
        (2, [1, 2], 10),
        (3, [1, 2, 3], 92)
    )

    def setUp(self):
        self.project_api_mock = mock.Mock()
        self.project_api_mock.get_workgroup_by_id = mock.Mock(return_value=_make_workgroup([]))
        self.runtime_mock = mock.create_autospec(spec=Runtime)
        self.runtime_mock.service = mock.Mock(return_value=None)
        self.block = GroupActivityXBlock(
            self.runtime_mock, field_data=DictFieldData({'weight': 100}), scope_ids=mock.Mock()
        )

        self.make_patch(GroupActivityXBlock, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        self.calculate_grade_mock = self.make_patch(self.block, 'calculate_grade')
        self.mark_complete = self.make_patch(self.block, 'mark_complete')

    @ddt.data(
        (1, [], 100),
        (2, [1, 2], 10),
        (3, [1, 2, 3], 92)
    )
    @ddt.unpack
    def test_marks_complete_for_workgroup(self, group_id, workgroup_users, grade):
        self.calculate_grade_mock.return_value = grade
        self.project_api_mock.get_workgroup_by_id.return_value = _make_workgroup(workgroup_users)

        self.block.calculate_and_send_grade(group_id)

        mark_complete_calls = self.block.mark_complete.call_args_list
        self.assertEqual(mark_complete_calls, [mock.call(user_id) for user_id in workgroup_users])

    @ddt.data(
        (1, 100, 'course1', 'content1', 100),
        (2, 10, 'course2', 'content2', 50),
        (3, 92, 'course3', 'contrent3', 150)
    )
    @ddt.unpack
    def test_sets_group_grade(self, group_id, grade, course_id, content_id, weight):
        self.calculate_grade_mock.return_value = grade
        self.block.weight = weight

        with mock.patch.object(GroupActivityXBlock, 'course_id', mock.PropertyMock(return_value=course_id)), \
                mock.patch.object(GroupActivityXBlock, 'content_id', mock.PropertyMock(return_value=content_id)):

            self.block.calculate_and_send_grade(group_id)

            self.project_api_mock.set_group_grade.assert_called_once_with(
                group_id, course_id, content_id, grade, weight
            )

    @ddt.data(1, 2, 3)
    def test_sends_notifications_message(self, group_id):
        self.calculate_grade_mock.return_value = 100
        # self.runtime_mock.service.return_value = None
        with mock.patch.object(self.block, 'fire_grades_posted_notification') as grades_posted_mock:
            self.block.calculate_and_send_grade(group_id)
            self.runtime_mock.service.assert_called_with(self.block, 'notifications')
            grades_posted_mock.assert_not_called()

            notifications_service_mock = mock.Mock()
            self.runtime_mock.service.return_value = notifications_service_mock

            self.block.calculate_and_send_grade(group_id)

            self.runtime_mock.service.assert_called_with(self.block, 'notifications')
            grades_posted_mock.assert_called_once_with(group_id, notifications_service_mock)

import ddt
from unittest import TestCase
from mock import mock
from group_project_v2.group_project import GroupActivityXBlock
from xblock.runtime import Runtime


from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock


def _make_question(question_id):
    question_mock = mock.Mock(spec=GroupProjectReviewQuestionXBlock)
    question_mock.question_id = question_id
    return question_mock


def _make_reviews(reviews):
    result = []
    for review in reviews:
        reviewer, question, answer = review
        result.append({'reviewer': reviewer, 'question': question, 'answer': answer})
    return result


class TestableGroupActivityXBlock(GroupActivityXBlock):
    _grade_questions = None
    _project_api = None

    def real_user_id(self, user_id):
        return user_id

    @property
    def project_api(self):
        return self._project_api

    @project_api.setter
    def project_api(self, value):
        self._project_api = value

    @property
    def grade_questions(self):
        return self._grade_questions

    @grade_questions.setter
    def grade_questions(self, value):
        self._grade_questions = value


@ddt.ddt
class TestGroupActivityXBlock(TestCase):
    def setUp(self):
        self.project_api_mock = mock.Mock()
        self.runtime_mock = self.get_runtime_mock()
        self.block = TestableGroupActivityXBlock(self.runtime_mock, field_data={}, scope_ids=mock.Mock())
        self.block.project_api = self.project_api_mock

    def get_runtime_mock(self):
        runtime = mock.Mock(spec=Runtime)
        return runtime

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
        self.block.grade_questions = [_make_question(question_id) for question_id in question_ids]

        grade = self.block.calculate_grade(group_id)
        self.assertEqual(grade, expected_grade)
        self.project_api_mock.get_workgroup_reviewers.assert_called_once_with(group_id, self.block.content_id)
        self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(
            group_id, self.block.content_id
        )

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
        self.block.grade_questions = [_make_question(question_id) for question_id in question_ids]

        grade = self.block.calculate_grade(group_id)
        self.assertEqual(grade, expected_grade)
        self.project_api_mock.get_workgroup_reviewers.assert_called_once_with(group_id, self.block.content_id)
        self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(
            group_id, self.block.content_id
        )


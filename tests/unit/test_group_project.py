import csv
from unittest import TestCase
from datetime import datetime
import pytz

import ddt
from freezegun import freeze_time
import mock
from xblock.fields import ScopeIds
from xblock.runtime import Runtime
from xblock.field_data import DictFieldData

from group_project_v2.group_project import GroupActivityXBlock, GroupProjectXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import ProjectDetails, WorkgroupDetails, ReducedUserDetails
from group_project_v2.stage import BaseGroupActivityStage, TeamEvaluationStage, PeerReviewStage
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock
from group_project_v2.utils import Constants
from tests.utils import TestWithPatchesMixin, make_review_item, parse_datetime


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
        self.block = GroupProjectXBlock(
            self.runtime_mock, field_data=DictFieldData({'display_name': 'Group Project'}), scope_ids=mock.Mock()
        )
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

    def test_download_incomplete_list_no_stage(self):
        request_mock = mock.Mock()
        request_mock.GET = {Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: 'missing_stage_id'}
        self.runtime_mock.get_block.return_value = None

        response = self.block.download_incomplete_list(request_mock)
        self.assertEqual(response.status_code, 404)

    @freeze_time(datetime(2015, 1, 1, 12, 22, 14))
    @ddt.data(
        ([1, 2, 3], [1], [2, 3]),
        ([1, 2, 3], [], [1, 2, 3]),
        ([1, 2, 3], [1, 2, 3], []),
    )
    @ddt.unpack
    def test_download_incomplete_list(self, all_users_ids, completed_users_ids, users_to_export_ids):
        request_mock = mock.Mock()
        request_mock.GET = {Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: 'target_stage_id'}

        target_stage = mock.Mock(spec=BaseGroupActivityStage)
        target_stage.display_name = 'Stage 1'
        target_stage.get_users_completion.return_value = (set(completed_users_ids), {'irrelevant'})

        self.runtime_mock.get_block.return_value = target_stage

        # pylint: disable=maybe-no-member
        expected_filename = GroupProjectXBlock.REPORT_FILENAME.format(
            group_project_name=self.block.display_name, stage_name=target_stage.display_name,
            timestamp=datetime.utcnow().strftime(GroupProjectXBlock.CSV_TIMESTAMP_FORMAT)
        )
        with mock.patch.object(self.block, 'export_users', mock.Mock(wraps=self.block.export_users)) as export_users, \
                mock.patch.object(self.block, 'get_workgroups_and_students') as patched_dashboard_params:
            patched_dashboard_params.return_value = (
                ['irrelevant'],
                [ReducedUserDetails(id=uid, first_name="irrelevant", last_name="irrelevant") for uid in all_users_ids]
            )

            response = self.block.download_incomplete_list(request_mock)
            actual_parameters = export_users.call_args_list

        self.assertEqual(response.status_code, 200)
        self.runtime_mock.get_block.assert_called_with('target_stage_id')
        self.assertEqual(len(actual_parameters), 1)
        args, kwargs = actual_parameters[0]
        self.assertEqual(len(args), 2)
        self.assertEqual(kwargs, {})
        self.assertEqual({user.id for user in args[0]}, set(users_to_export_ids))
        self.assertEqual(args[1], expected_filename)

    def test_download_incomplete_list_csv_contents(self):
        request_mock = mock.Mock()
        request_mock.GET = {Constants.ACTIVATE_BLOCK_ID_PARAMETER_NAME: 'target_stage_id'}

        target_stage = mock.Mock(spec=BaseGroupActivityStage)
        target_stage.display_name = 'Stage 1'
        target_stage.get_users_completion.return_value = ({1}, {'irrelevant'})
        all_users = [
            ReducedUserDetails(id=1, first_name="U1", last_name="U1", username='U1', email="u1@example.org"),
            ReducedUserDetails(id=2, first_name="U2", last_name="U2", username='U2', email="u2@example.org"),
            ReducedUserDetails(id=3, first_name="U3", last_name="U3", username='U3', email="u3@example.org"),
        ]

        def csv_repr(user):
            return {"Name": user.full_name, 'Email': user.email, 'Username': user.username}

        self.runtime_mock.get_block.return_value = target_stage

        with mock.patch.object(self.block, 'get_workgroups_and_students') as patched_dashboard_params:
            patched_dashboard_params.return_value = (['irrelevant'], all_users)

            response = self.block.download_incomplete_list(request_mock)

        self.assertEqual(response.status_code, 200)
        # pylint: disable=unnecessary-comprehension
        reader = csv.DictReader([line for line in response.text.split("\n")])
        lines = [line for line in reader]
        self.assertEqual(reader.fieldnames, GroupProjectXBlock.CSV_HEADERS)
        self.assertEqual(lines[0], csv_repr(all_users[1]))
        self.assertEqual(lines[1], csv_repr(all_users[2]))


@ddt.ddt
class TestGroupActivityXBlock(TestWithPatchesMixin, TestCase):
    def setUp(self):
        super(TestGroupActivityXBlock, self).setUp()
        self.project_api_mock = mock.Mock(spec=TypedProjectAPI)
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.scope_ids_mock = mock.Mock(spec=ScopeIds)
        self.block = GroupActivityXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=self.scope_ids_mock)
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
        (None, []),
        (None, [None, None, None]),
        ('2016-02-27 08:00:00', ['2016-02-26 04:30:48', None, '2016-02-27 08:00:00']),
        ('2016-10-29 04:30:48', ['2016-02-26 04:30:48', None, '2016-10-29 04:30:48', None]),
        ('2016-10-29 04:30:48', ['2016-02-26 04:30:48', '2016-10-29 04:30:48', '2016-02-29 04:30:48']),
        ('2016-10-29 04:30:48', ['2016-10-29 04:30:48', '2016-02-26 04:30:48', '2016-02-29 04:30:48']),
        ('2016-10-29 04:30:48', ['2016-02-26 04:30:48', '2016-02-29 04:30:48', '2016-10-29 04:30:48']),
        ('2016-10-29 04:30:48', ['2016-02-26 04:30:48', '2016-10-29 04:30:48', '2016-10-29 04:30:48']),
        ('2016-11-30 04:30:48', ['2016-11-30 04:30:48', '2016-10-29 04:30:48', '2016-02-26 04:30:48']),
        ('2016-12-29 12:30:49', ['2016-12-29 12:30:47', '2016-12-29 12:30:48', '2016-12-29 12:30:49']),
    )
    @ddt.unpack
    def test_get_grade_display_stage(self, expected_result, grade_display_dates):
        stages = []
        for display_datetime in grade_display_dates:
            stage_mock = mock.create_autospec(BaseGroupActivityStage)
            stage_mock.open_date = parse_datetime(display_datetime)
            stages.append(stage_mock)

        with mock.patch.object(self.block, 'get_children_by_category', mock.Mock()) as get_stages:
            get_stages.return_value = stages
            self.assertEqual(
                getattr(self.block.get_grade_display_stage(), "open_date", None), parse_datetime(expected_result)
            )


@ddt.ddt
class TestGetDashboardURL(TestWithPatchesMixin, TestCase):
    def setUp(self):
        super(TestGetDashboardURL, self).setUp()
        self.runtime_mock = mock.Mock(spec=Runtime)
        self.runtime_mock.course_id = 'course_id'
        self.scope_ids_mock = mock.Mock(spec=ScopeIds)
        self.block = GroupActivityXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=self.scope_ids_mock)
        self.user_pref_mock = self.make_patch(
            GroupActivityXBlock, 'user_preferences', mock.PropertyMock(return_value={})
        )
        self.project_mock = mock.Mock()
        self.project_mock.scope_ids.usage_id = 'project1'
        self.make_patch(GroupActivityXBlock, 'project', self.project_mock)

        self.settings_service_mock = mock.Mock()
        self.runtime_mock.service = mock.Mock(return_value=self.settings_service_mock)

    @staticmethod
    def _get_dashboard_url(template, program_id=None, course_id=None, project_id=None, activity_id=None):
        return template.format(
            program_id=program_id, course_id=course_id, project_id=project_id, activity_id=activity_id
        )

    @ddt.data('activity_1', 'activity_2', 'activity_92', 'qweasdzxc')
    def test_dashboard_details_url_no_service(self, block_id):
        self.runtime_mock.service.return_value = None
        self.scope_ids_mock.usage_id = block_id
        expected_url = self._get_dashboard_url(
            GroupActivityXBlock.DEFAULT_DASHBOARD_DETAILS_URL_TPL,
            activity_id=block_id
        )

        url = self.block.dashboard_details_url()

        self.assertEqual(url, expected_url)
        self.runtime_mock.service.assert_called_once_with(self.block, 'settings')

    @ddt.data('activity_1', 'activity_2', 'activity_92', 'qweasdzxc')
    def test_dashboard_details_url_no_settings(self, block_id):
        self.settings_service_mock.get_settings_bucket = mock.Mock(return_value=None)
        self.scope_ids_mock.usage_id = block_id
        expected_url = self._get_dashboard_url(
            GroupActivityXBlock.DEFAULT_DASHBOARD_DETAILS_URL_TPL,
            activity_id=block_id
        )

        url = self.block.dashboard_details_url()

        self.assertEqual(url, expected_url)
        self.settings_service_mock.get_settings_bucket.assert_called_once_with(self.block)

    @ddt.data('activity_1', 'activity_2', 'activity_92', 'qweasdzxc')
    def test_dashboard_details_url_no_settings_key(self, block_id):
        self.settings_service_mock.get_settings_bucket = mock.Mock(return_value={})
        self.scope_ids_mock.usage_id = block_id
        expected_url = self._get_dashboard_url(
            GroupActivityXBlock.DEFAULT_DASHBOARD_DETAILS_URL_TPL,
            activity_id=block_id
        )

        url = self.block.dashboard_details_url()

        self.assertEqual(url, expected_url)
        self.settings_service_mock.get_settings_bucket.assert_called_once_with(self.block)

    @ddt.data(
        ('qwe', 'na', 'na', 'na', 'na', 'qwe'),
        ('zxc?activity_id={activity_id}', 'activity_2', 'na', 'na', 'na', 'zxc?activity_id=activity_2'),
        ('?activate_block_id={activity_id}', 'activity_92', 'na', 'na', 'na', '?activate_block_id=activity_92'),
        ('/part1/part2/{activity_id}', 'qweasdzxc', 'na', 'na', 'na', '/part1/part2/qweasdzxc'),
        ('/{program_id}/part2/{activity_id}', 'act_1', 'prog_1', 'na', 'na', '/prog_1/part2/act_1'),
        ('/{program_id}/{course_id}/{activity_id}', 'act_2', 'prog_2', 'c_2', 'na', '/prog_2/c_2/act_2'),
        (
            '/{program_id}/{course_id}/{project_id}?act={activity_id}',
            'act_3', 'prog_3', 'c_3', 'proj_3', '/prog_3/c_3/proj_3?act=act_3'
        ),
    )
    @ddt.unpack
    def test_dashboard_details_url_setting_present(  # pylint:disable=too-many-arguments
            self, setting_value, block_id, preferences_program, course_id, project_id, expected_url
    ):
        self.settings_service_mock.get_settings_bucket = mock.Mock(
            return_value={GroupActivityXBlock.DASHBOARD_DETAILS_URL_KEY: setting_value}
        )
        self.scope_ids_mock.usage_id = block_id
        self.project_mock.scope_ids.usage_id = project_id
        self.runtime_mock.course_id = course_id
        self.user_pref_mock.return_value = {self.block.DASHBOARD_PROGRAM_ID_KEY: preferences_program}

        url = self.block.dashboard_details_url()

        self.assertEqual(url, expected_url)
        self.settings_service_mock.get_settings_bucket.assert_called_once_with(self.block)


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
        (6, ["q1", "q2"], [1], [(1, "q1", 1), (1, "q2", 2)], round((1.0 + 2.0) / 2.0)),  # rounding
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
            return_value=_make_reviews(reviews) + _make_reviews(admin_reviews)
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
        (3, [1, 2, 3], 92),
        (4, [1, 2, 3, 4], 0)
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
        (3, 92, 'course3', 'content3', 150),
        (4, 0, 'course4', 'content4', 200)
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
        stage_mock = mock.create_autospec(BaseGroupActivityStage)
        stage_mock.open_date = datetime.now().replace(tzinfo=pytz.UTC)  # pylint: disable=maybe-no-member

        with mock.patch.object(GroupActivityXBlock, 'get_grade_display_stage', return_value=stage_mock):
            with mock.patch.object(stage_mock, 'fire_grades_posted_notification') as grades_posted_mock:
                self.block.calculate_and_send_grade(group_id)
                self.runtime_mock.service.assert_called_with(self.block, 'notifications')
                grades_posted_mock.assert_not_called()

                notifications_service_mock = mock.Mock()
                self.runtime_mock.service.return_value = notifications_service_mock

                self.block.calculate_and_send_grade(group_id)

                self.runtime_mock.service.assert_called_with(self.block, 'notifications')
                grades_posted_mock.assert_called_once_with(
                    group_id, notifications_service_mock
                )

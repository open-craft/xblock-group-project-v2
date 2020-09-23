""" Tests for Base Stage Class """
from builtins import range
from collections import OrderedDict

import ddt
import mock
from group_project_v2.project_api.dtos import ReducedUserDetails

from group_project_v2.stage import BaseGroupActivityStage
from group_project_v2.stage.utils import StageState
from group_project_v2.utils import Constants
from tests.unit.test_stages.base import BaseStageTest
from tests.utils import WORKGROUP, KNOWN_USERS, OTHER_GROUPS, TestConstants


TEST_USERS = TestConstants.Users  # pylint: disable=invalid-name


class DummyStageBlock(BaseGroupActivityStage):
    """ Dummy stage for testing BaseGroupActivityStage """

    def get_users_completion(self, target_workgroups, target_users):
        pass

    def get_stage_state(self):
        pass

    def can_access_dashboard(self, user_id):
        """
        Checks if given user can access dashboard.
        :param user_id:
        :return: True if user can access dashboard.
        :rtype: bool
        """
        return True


def make_stats(completed, partially_complete, not_started):
    """
    Helper method to build stats dictionary as returned by get_dashboard_stage_state
    :param completed: ratio of students completed the stage as float in [0..1] interval
    :type completed: float | None
    :param partially_complete: ratio of students partially completed the stage as float in [0..1] interval
    :type partially_complete: float | None
    :param not_started: ratio of student not started the stage as float in [0..1] interval
    :type not_started: float | None
    :rtype: dict[str, float | None]
    :return: Ratios of students complete, partially competed and not started the stage
    """
    return {
        StageState.NOT_STARTED: not_started,
        StageState.INCOMPLETE: partially_complete,
        StageState.COMPLETED: completed
    }


def make_reduced_user_details(**kwargs):
    defaults = {
        'id': 1,
        'username': 'test.user',
        'email': 'test.user@example.com',
        'first_name': 'test',
        'last_name': 'user'
    }
    defaults.update(kwargs)
    return ReducedUserDetails(**kwargs)


def make_context(workgroups, target_students, filtered_students):
    """
    Helper method - builds context with values expected by dahsboard_view
    :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] workgroups:
    :param collections.Iterable[group_project_v2.project_api.dtos.UserDetails] target_students:
    :param collections.Iterable[int] filtered_students:
    :return:
    """
    return {
        Constants.TARGET_WORKGROUPS: workgroups,
        Constants.TARGET_STUDENTS: target_students,
        Constants.FILTERED_STUDENTS: filtered_students
    }


@ddt.ddt
class TestBaseGroupActivityStage(BaseStageTest):
    """ Tests for Base Stage Class """
    block_to_test = DummyStageBlock

    def setUp(self):
        super(TestBaseGroupActivityStage, self).setUp()
        self.render_template_patch = self.make_patch(self.block, 'render_template')

    def test_stage_is_not_graded(self):
        self.assertFalse(self.block.is_graded_stage)

    def test_stage_is_not_shown_on_detail_dashboard(self):
        self.assertFalse(self.block.shown_on_detail_view)

    # invalid name in order to match camlCase naming of assertSomething methods
    def assertDictionaryEqual(self, actual, expected, strict=False):  # pylint: disable=invalid-name
        """
        Less strict assert for dictionary equality - checks that `actual` contains all the keys from expected, and
        values match. If `strict` is true, also checks that no other keys are present in the `actual` (roughly equal
        to plain assertEqual)
        :param dict[Any, Any] actual: actual result
        :param dict[Any, ANy] expected: expected result
        :param bool strict: Strict comparison:
            If set to False allows `actual` to contain keys not found in `expected`.
            If True - requires that no other keys are present in `actual` - roughly equivalent to plain assertEqual
        """
        for key, value in expected.items():
            self.assertIn(key, actual)
            self.assertEqual(actual[key], value)

        if strict:
            self.assertEqual(list(actual.keys()), list(expected.keys()))

    @ddt.data(
        ([WORKGROUP], list(KNOWN_USERS.values()), StageState.COMPLETED, make_stats(1.0, 0, 0)),
        ([WORKGROUP], list(KNOWN_USERS.values()), StageState.INCOMPLETE, make_stats(0.3, 0.4, 0.3)),
        (OTHER_GROUPS, list(KNOWN_USERS.values()), StageState.INCOMPLETE, make_stats(0.3, 0.4, 0.3)),
        (OTHER_GROUPS, list(KNOWN_USERS.values()), StageState.NOT_STARTED, make_stats(0.0, 0.0, 1.0)),
    )
    @ddt.unpack
    def test_dashboard_view(self, workgroups, target_students, state, stats):
        render_template_response = u'render_template_response'
        is_ta_graded = False
        patched_stats = self.make_patch(self.block, 'get_dashboard_stage_state')
        patched_stats.return_value = (state, stats)
        type(self.activity_mock).is_ta_graded = mock.PropertyMock(return_value=is_ta_graded)
        self.render_template_patch.return_value = render_template_response

        context = make_context(workgroups, target_students, [])

        expected_human_stats = BaseGroupActivityStage.make_human_stats(stats)
        expected_context = {
            'stage': self.block, 'stats': expected_human_stats, 'stage_state': state, 'ta_graded': is_ta_graded
        }

        with mock.patch('group_project_v2.stage.base.Fragment.add_content') as patched_add_content:
            self.block.dashboard_view(context)

            patched_add_content.assert_called_once_with(render_template_response)

        # single call - roughly equivalent to assert_called_once_with(...)
        self.assertEqual(len(self.render_template_patch.call_args_list), 1)
        args, kwargs = self.render_template_patch.call_args_list[0]
        self.assertEqual(kwargs, {})
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0], 'dashboard_view')
        self.assertDictionaryEqual(args[1], expected_context)

    @ddt.data(
        (make_stats(0.4, 0.3, 0.4), (40, 30, 40)),
        (make_stats(0.1, 0.1, 0.8), (80, 10, 10)),
        (make_stats(None, None, None), (None, None, None))
    )
    @ddt.unpack
    def test_make_human_stats(self, stats, human_stats_data):
        stats_order = (StageState.NOT_STARTED, StageState.INCOMPLETE, StageState.COMPLETED)
        actual_human_stats = BaseGroupActivityStage.make_human_stats(stats)

        expected_human_stats = OrderedDict([
            (StageState.get_human_name(stats_order[idx]), human_stats_data[idx])
            for idx in range(3)
        ])

        self.assertEqual(list(actual_human_stats.keys()), list(expected_human_stats.keys()))

        for idx, human_stat in enumerate(expected_human_stats.items()):
            stat_name, stat_value = human_stat
            actual_stat_value = actual_human_stats[stat_name]
            self.assertAlmostEqual(stat_value, actual_stat_value)

    @ddt.data(
        # not filtered - pass all students
        ([WORKGROUP], list(KNOWN_USERS.values()), [], list(KNOWN_USERS.values())),
        # single filter hit - pass all except that student
        (
            [WORKGROUP], list(KNOWN_USERS.values()), [TEST_USERS.USER1_ID],
            [KNOWN_USERS[TEST_USERS.USER2_ID], KNOWN_USERS[TEST_USERS.USER3_ID]]
        ),
        # multiple filter hits - pass all except that students
        (
            [WORKGROUP], list(KNOWN_USERS.values()), [TEST_USERS.USER1_ID, TEST_USERS.USER3_ID],
            [KNOWN_USERS[TEST_USERS.USER2_ID]]
        ),
        # filter "miss" - pass all
        ([WORKGROUP], list(KNOWN_USERS.values()), [TEST_USERS.UNKNOWN_USER], list(KNOWN_USERS.values())),
        # filter hit and miss - pass all expcept hit
        (
            [WORKGROUP], list(KNOWN_USERS.values()), [TEST_USERS.USER2_ID, TEST_USERS.UNKNOWN_USER],
            [KNOWN_USERS[TEST_USERS.USER1_ID], KNOWN_USERS[TEST_USERS.USER3_ID]]
        ),
        # filtered all - pass no students
        (
            [WORKGROUP], list(KNOWN_USERS.values()), [TEST_USERS.USER1_ID, TEST_USERS.USER2_ID, TEST_USERS.USER3_ID],
            []
        ),
    )
    @ddt.unpack
    def test_dashboard_view_filters_students(self, workgroups, target_students, filtered_students, expected_students):
        patched_stats = self.make_patch(self.block, 'get_dashboard_stage_state')
        patched_stats.return_value = (StageState.COMPLETED, make_stats(1.0, 0.0, 0.0))
        context = make_context(workgroups, target_students, filtered_students)

        with mock.patch('group_project_v2.stage.base.Fragment.add_content'):
            self.block.dashboard_view(context)

        patched_stats.assert_called_once_with(workgroups, expected_students)

    @ddt.data(
        ([1], [1], [], make_stats(1, 0, 0), True),
        (list(range(10)), list(range(3)), list(range(3, 6)), make_stats(.3, .3, .4), True),
        ([], [], [], make_stats(None, None, None), False),
    )
    @ddt.unpack
    def test_get_stage_stats(
            self, all_user_ids, completed_user_ids, partial_user_ids, expected_stats, completions_called):
        all_users = [make_reduced_user_details(id=user_id) for user_id in all_user_ids]
        completed_user_ids = set(completed_user_ids)
        partial_user_ids = set(partial_user_ids)
        patched_completions = self.make_patch(self.block, 'get_users_completion')
        self.block.display_name = "dummy block"  # pylint: disable=attribute-defined-outside-init
        patched_completions.return_value = (completed_user_ids, partial_user_ids)

        target_workgroups = tuple()

        stats = self.block.get_stage_stats(target_workgroups, all_users)
        if completions_called:
            patched_completions.assert_called_once_with(target_workgroups, all_users)
        else:
            self.assertFalse(patched_completions.called)

        self.assertEqual(len(expected_stats), len(stats))

        for stat, value in list(stats.items()):
            self.assertAlmostEqual(value, expected_stats[stat])

    def test_get_external_group_status(self):
        self.assertEqual(self.block.get_external_group_status('irrelevant'), StageState.NOT_AVAILABLE)

    def test_get_external_status_label(self):
        self.assertEqual(self.block.get_external_status_label('irrelevant'), self.block.DEFAULT_EXTERNAL_STATUS_LABEL)

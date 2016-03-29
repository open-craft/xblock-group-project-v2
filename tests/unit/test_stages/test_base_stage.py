""" Tests for Base Stage Class """
from collections import OrderedDict

import ddt
import mock

from group_project_v2.stage import BaseGroupActivityStage
from group_project_v2.stage.utils import StageState
from group_project_v2.utils import Constants
from tests.unit.test_stages.base import BaseStageTest
from tests.utils import WORKGROUP, KNOWN_USERS, OTHER_GROUPS, TestConstants


TEST_USERS = TestConstants.Users


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
    :param float completed: ratio of students completed the stage as float in [0..1] interval
    :param float partially_complete: ratio of students partially completed the stage as float in [0..1] interval
    :param float not_started: ratio of student not started the stage as float in [0..1] interval
    :rtype: dict[str, float]
    :return: Ratios of students complete, partially competed and not started the stage
    """
    return {
        StageState.NOT_STARTED: not_started,
        StageState.INCOMPLETE: partially_complete,
        StageState.COMPLETED: completed
    }


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


def get_human_stats(completed, partially_complete, not_started):
    """
    Helper method - converts machine-friendly stage stats to human-friendly stage stats
    :param float completed: ratio of students completed the stage as float in [0..1] interval
    :param float partially_complete: ratio of students partially completed the stage as float in [0..1] interval
    :param float not_started: ratio of student not started the stage as float in [0..1] interval
    :rtype: dict[str, float]
    """
    return OrderedDict([
        (StageState.get_human_name(StageState.NOT_STARTED), not_started*100),
        (StageState.get_human_name(StageState.INCOMPLETE), partially_complete*100),
        (StageState.get_human_name(StageState.COMPLETED), completed*100),
    ])


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
        for key, value in expected.iteritems():
            self.assertIn(key, actual)
            self.assertEqual(actual[key], value)

        if strict:
            self.assertEqual(actual.keys(), expected.keys())

    @ddt.data(
        ([WORKGROUP], KNOWN_USERS.values(), StageState.COMPLETED, make_stats(1.0, 0, 0)),
        ([WORKGROUP], KNOWN_USERS.values(), StageState.INCOMPLETE, make_stats(0.3, 0.4, 0.3)),
        (OTHER_GROUPS, KNOWN_USERS.values(), StageState.INCOMPLETE, make_stats(0.3, 0.4, 0.3)),
        (OTHER_GROUPS, KNOWN_USERS.values(), StageState.NOT_STARTED, make_stats(0.0, 0.0, 1.0)),
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

        expected_human_stats = get_human_stats(
            stats[StageState.COMPLETED], stats[StageState.INCOMPLETE], stats[StageState.NOT_STARTED]
        )
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
        # not filtered - pass all students
        ([WORKGROUP], KNOWN_USERS.values(), [], KNOWN_USERS.values()),
        # single filter hit - pass all except that student
        (
            [WORKGROUP], KNOWN_USERS.values(), [TEST_USERS.USER1_ID],
            [KNOWN_USERS[TEST_USERS.USER2_ID], KNOWN_USERS[TEST_USERS.USER3_ID]]
        ),
        # multiple filter hits - pass all except that students
        (
            [WORKGROUP], KNOWN_USERS.values(), [TEST_USERS.USER1_ID, TEST_USERS.USER3_ID],
            [KNOWN_USERS[TEST_USERS.USER2_ID]]
        ),
        # filter "miss" - pass all
        ([WORKGROUP], KNOWN_USERS.values(), [TEST_USERS.UNKNOWN_USER], KNOWN_USERS.values()),
        # filter hit and miss - pass all expcept hit
        (
            [WORKGROUP], KNOWN_USERS.values(), [TEST_USERS.USER2_ID, TEST_USERS.UNKNOWN_USER],
            [KNOWN_USERS[TEST_USERS.USER1_ID], KNOWN_USERS[TEST_USERS.USER3_ID]]
        ),
        # filtered all - pass no students
        (
            [WORKGROUP], KNOWN_USERS.values(), [TEST_USERS.USER1_ID, TEST_USERS.USER2_ID, TEST_USERS.USER3_ID],
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

    def test_get_external_group_status(self):
        self.assertEqual(self.block.get_external_group_status('irrelevant'), StageState.NOT_AVAILABLE)

    def test_get_external_status_label(self):
        self.assertEqual(self.block.get_external_status_label('irrelevant'), self.block.DEFAULT_EXTERNAL_STATUS_LABEL)

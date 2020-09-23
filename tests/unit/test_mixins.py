from __future__ import print_function
# pylint:disable=protected-access,no-self-use,invalid-name

from builtins import str
from builtins import object
from unittest import TestCase

import ddt
import mock
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
from xblock.core import XBlock
from xblock.runtime import Runtime

from group_project_v2.mixins import (
    ChildrenNavigationXBlockMixin, CourseAwareXBlockMixin, UserAwareXBlockMixin,
    WorkgroupAwareXBlockMixin, DashboardRootXBlockMixin,
    AuthXBlockMixin
)
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import WorkgroupDetails, UserGroupDetails
from group_project_v2.utils import GroupworkAccessDeniedError, Constants
from tests.utils import (
    TestWithPatchesMixin, raise_api_error, MockedAuthXBlockMixin,
    get_mock_project_api
)


def _make_block_mock(block_id, category=None):
    result = mock.create_autospec(XBlock)

    result.usage_id = block_id

    result.category = category or 'xblock_category'
    return result


def _make_user_mock(user_id):
    result = mock.Mock(spec={})
    result.id = user_id
    return result


class CommonMixinGuineaPig(object):
    @property
    def runtime(self):
        return None


class ChildrenNavigationXBlockMixinGuineaPig(ChildrenNavigationXBlockMixin, CommonMixinGuineaPig):
    @property
    def children(self):
        return None


class TestChildrenNavigationXBlockMixin(TestWithPatchesMixin, TestCase):
    def setUp(self):
        self.block = ChildrenNavigationXBlockMixinGuineaPig()
        self.runtime_mock = mock.create_autospec(Runtime)
        self.make_patch(
            ChildrenNavigationXBlockMixinGuineaPig, 'runtime',
            mock.PropertyMock(return_value=self.runtime_mock)
        )
        self.children_mock = self.make_patch(
            ChildrenNavigationXBlockMixinGuineaPig, 'children', mock.PropertyMock())
        self.runtime_mock.get_block.side_effect = _make_block_mock

    def test_children(self):
        self.children_mock.return_value = ['block_1', 'block_2', 'block_3']
        children = self.block._children
        self.assertEqual(len(children), 3)
        self.assertEqual(children[0].usage_id, 'block_1')
        self.assertEqual(children[1].usage_id, 'block_2')
        self.assertEqual(children[2].usage_id, 'block_3')

    def test_child_category(self):
        child_with_category = mock.Mock(spec={})
        child_with_category.category = 'category_1'

        child_with_plugin_name = mock.Mock(spec={})
        child_with_plugin_name.plugin_name = 'category 2'

        child_with_plugin_name_and_category = mock.Mock(spec={})
        child_with_plugin_name_and_category.category = 'category_3'
        child_with_plugin_name_and_category.plugin_name = 'category 4'

        child_with_no_target_props = mock.Mock(spec={})

        self.assertEqual(self.block.get_child_category(
            child_with_category), child_with_category.category)
        self.assertEqual(self.block.get_child_category(
            child_with_plugin_name), child_with_plugin_name.plugin_name)
        self.assertEqual(
            self.block.get_child_category(child_with_plugin_name_and_category),
            child_with_plugin_name_and_category.category
        )
        self.assertEqual(self.block.get_child_category(
            child_with_no_target_props), None)

    def test_get_children_by_category(self):
        child_categories = {
            'block_1': 'category_1',
            'block_1_2': 'category_1',
            'block_2': 'category_2',
            'block_3': 'category_3'
        }
        self.children_mock.return_value = [
            'block_1', 'block_1_2', 'block_2', 'block_3']
        self.runtime_mock.get_block.side_effect = lambda block_id: _make_block_mock(
            block_id, child_categories.get(block_id, None)
        )

        def do_assert(expected_ids, *categories):
            response = self.block.get_children_by_category(*categories)
            response_ids = [block.usage_id for block in response]
            self.assertEqual(response_ids, expected_ids)

        do_assert(['block_1', 'block_1_2'], 'category_1')
        do_assert(['block_2'], 'category_2')
        do_assert(['block_3'], 'category_3')
        do_assert(['block_2', 'block_3'], 'category_2', 'category_3')
        do_assert([], 'missing_category')

        self.assertEqual(self.block.get_child_of_category('category_1').usage_id, 'block_1')
        self.assertEqual(self.block.get_child_of_category('category_2').usage_id, 'block_2')
        self.assertEqual(self.block.get_child_of_category('category_3').usage_id, 'block_3')

        self.assertIsNone(self.block.get_child_of_category('missing_category'))
        self.assertIsNone(self.block.get_child_of_category('other_missing_category'))

    def test_has_child_of_category(self):
        def _make_block_usage(block_id, block_type):
            result = mock.Mock(spec=BlockUsageLocator)
            result.block_type = block_type
            result.block_id = block_id
            return result

        self.children_mock.return_value = [
            _make_block_usage('block_1', 'category_1'),
            _make_block_usage('block_1_2', 'category_1'),
            _make_block_usage('block_2', 'category_2'),
            _make_block_usage('block_3', 'category_3'),
        ]
        self.assertTrue(self.block.has_child_of_category('category_1'))
        self.assertTrue(self.block.has_child_of_category('category_2'))
        self.assertTrue(self.block.has_child_of_category('category_3'))
        self.assertFalse(self.block.has_child_of_category('missing_category'))
        self.assertFalse(self.block.has_child_of_category('other_missing_category'))

    def test_render_children(self):
        child1, child2 = mock.Mock(), mock.Mock()
        view1, context1 = 'nav_view', {'qwe': 'asd'}

        with mock.patch.object(type(self.block), '_children', mock.PropertyMock(return_value=[child1, child2])):
            self.block._render_children(view1, context1)

        child1.render.assert_called_once_with(view1, context1)
        child2.render.assert_called_once_with(view1, context1)
        child1.reset_mock()
        child2.reset_mock()

        view2, context2 = 'other_view', {'rty', 'fgh'}
        self.block._render_children(view2, context2, [child1])
        child1.render.assert_called_once_with(view2, context2)
        self.assertFalse(child2.render.called)


class CourseAwareXBlockMixinGuineaPig(CommonMixinGuineaPig, CourseAwareXBlockMixin):
    pass


@ddt.ddt
class TestCourseAwareXBlockMixin(TestCase, TestWithPatchesMixin):
    def setUp(self):
        self.block = CourseAwareXBlockMixinGuineaPig()
        self.runtime_mock = mock.create_autospec(Runtime)
        self.make_patch(
            CourseAwareXBlockMixinGuineaPig, 'runtime',
            mock.PropertyMock(return_value=self.runtime_mock)
        )

    @ddt.data(
        'string_course_id',
        u'unicode_course_id',
        CourseLocator(org='123', course='456', run='789')
    )
    def test_course_id(self, course_id):
        self.runtime_mock.course_id = course_id
        self.assertEqual(self.block.course_id, str(course_id))


class UserAwareXBlockMixinGuineaPig(CommonMixinGuineaPig, UserAwareXBlockMixin):
    pass


@ddt.ddt
class TestUserAwareXBlockMixin(TestCase, TestWithPatchesMixin):
    def setUp(self):
        UserAwareXBlockMixinGuineaPig._known_real_user_ids = {}
        self.block = UserAwareXBlockMixinGuineaPig()
        self.runtime_mock = mock.create_autospec(Runtime)
        self.make_patch(
            UserAwareXBlockMixinGuineaPig, 'runtime',
            mock.PropertyMock(return_value=self.runtime_mock)
        )

    @ddt.data('1', '12', 'student1')
    def test_anonymous_student_id(self, student_id):
        self.runtime_mock.anonymous_student_id = student_id
        self.assertEqual(self.block.anonymous_student_id, student_id)

    @ddt.data('1', '12', 'student1')
    def test_anonymous_student_id_no_runtime_attribute(self, student_id):
        self.runtime_mock.user_id = student_id
        self.assertEqual(self.block.anonymous_student_id, student_id)

    def test_real_user_id(self):
        real_users = {'u1': _make_user_mock(1), 'u2': _make_user_mock(2), 'u3': _make_user_mock(3)}
        self.runtime_mock.get_real_user = mock.Mock(side_effect=lambda u_id: real_users.get(u_id, None))
        self.assertEqual(self.block.real_user_id('u1'), 1)
        self.assertEqual(self.block.real_user_id('u2'), 2)
        self.assertEqual(self.block.real_user_id('u3'), 3)

        del self.runtime_mock.get_real_user
        # these three are cached
        self.assertEqual(self.block.real_user_id('u1'), 1)
        self.assertEqual(self.block.real_user_id('u2'), 2)
        self.assertEqual(self.block.real_user_id('u3'), 3)

        # these three are not
        self.assertEqual(self.block.real_user_id('u4'), 'u4')
        self.assertEqual(self.block.real_user_id('u5'), 'u5')
        self.assertEqual(self.block.real_user_id('u6'), 'u6')

    @ddt.data(
        ('u1', 1),  # via get_real_user
        ('u2', 2),  # via get_real_user
        ('12', 12),  # get_real_user throws - via int conversion
        ('u3', None),  # get_real_user and in conversion throws - return None
        ('qwerty', None)  # get_real_user and in conversion throws - return None
    )
    @ddt.unpack
    def test_user_id_property(self, user_id, expected_result):
        self.runtime_mock.user_id = user_id
        real_users = {'u1': _make_user_mock(1), 'u2': _make_user_mock(2)}
        self.runtime_mock.get_real_user = mock.Mock(side_effect=lambda u_id: real_users.get(u_id, None))

        self.assertEqual(self.block.user_id, expected_result)


class WorkgroupAwareXBlockMixinGuineaPig(CommonMixinGuineaPig, WorkgroupAwareXBlockMixin):
    @property
    def project_api(self):
        return None

    @property
    def user_id(self):
        return None

    @property
    def course_id(self):
        return None


@ddt.ddt
class TestWorkgroupAwareXBlockMixin(TestCase, TestWithPatchesMixin):
    def setUp(self):
        self.block = WorkgroupAwareXBlockMixinGuineaPig()
        self.project_api_mock = mock.create_autospec(TypedProjectAPI)
        self.make_patch(
            WorkgroupAwareXBlockMixinGuineaPig, 'project_api',
            mock.PropertyMock(return_value=self.project_api_mock)
        )

        self.user_id_mock = self.make_patch(WorkgroupAwareXBlockMixinGuineaPig, 'user_id', mock.PropertyMock())
        self.course_id_mock = self.make_patch(WorkgroupAwareXBlockMixinGuineaPig, 'course_id', mock.PropertyMock())

        self.project_api_mock.get_user_preferences = mock.Mock()
        self.project_api_mock.get_workgroup_by_id = mock.Mock()
        self.project_api_mock.get_user_workgroup_for_course = mock.Mock()
        self.project_api_mock.get_user_roles_for_course = mock.Mock()

    def test_fallback_workgroup(self):
        self.project_api_mock.get_user_preferences.side_effect = lambda u_id: raise_api_error(401, "qwerty")

        self.assertEqual(self.block.workgroup, WorkgroupAwareXBlockMixin.FALLBACK_WORKGROUP)

    @ddt.data(
        (1, 'course', {'users': [1], 'id': 12}),
        (4, 'other-course', {'users': [1, 2, 3, 4], 'id': 1})
    )
    @ddt.unpack
    def test_non_ta_path(self, user_id, course_id, workgroup):
        self.user_id_mock.return_value = user_id
        self.course_id_mock.return_value = course_id
        self.project_api_mock.get_user_preferences.return_value = {}
        self.project_api_mock.get_user_workgroup_for_course.return_value = workgroup

        self.assertEqual(self.block.workgroup, workgroup)

        self.project_api_mock.get_user_preferences.assert_called_once_with(user_id)
        self.project_api_mock.get_user_workgroup_for_course.assert_called_once_with(
            user_id, course_id
        )

    @ddt.data(
        (1, {'users': [1], 'id': 12}),
        (2, {'users': [1, 2, 3, 4], 'id': 1})
    )
    @ddt.unpack
    def test_ta_path(self, pref_group_id, workgroup):
        self.project_api_mock.get_user_preferences.return_value = {
            WorkgroupAwareXBlockMixin.TA_REVIEW_KEY: pref_group_id
        }
        self.project_api_mock.get_workgroup_by_id.return_value = workgroup

        with mock.patch.object(WorkgroupAwareXBlockMixin, 'is_user_ta'):
            # patched_check is noop if everything is ok, so we're letting it return a mock, or whatever it pleases
            self.assertEqual(self.block.workgroup, workgroup)
            self.project_api_mock.get_workgroup_by_id.assert_called_once_with(pref_group_id)

    def test_outsider_disallowed_propagates(self):
        self.project_api_mock.get_user_preferences.return_value = {WorkgroupAwareXBlockMixin.TA_REVIEW_KEY: 1}

        with mock.patch.object(WorkgroupAwareXBlockMixin, 'is_user_ta') as patched_check:
            patched_check.return_value = False

            self.assertRaises(GroupworkAccessDeniedError, lambda: self.block.workgroup)
            patched_check.assert_called_with(self.block.user_id, self.block.course_id)

    @ddt.data(
        (1, 'qwe', ['role1'], ['role1', 'role2']),
        (2, 'asd', ['qwe', 'asd'], ['qwe', 'rty']),
        (3, 'course_id', ['123', '456'], ['123', '456']),
    )
    @ddt.unpack
    def test_is_ta(self, user_id, course_id, user_roles, allowed_roles):
        self.project_api_mock.get_user_roles_for_course.return_value = set(user_roles)
        with mock.patch.object(AuthXBlockMixin, 'ta_roles', allowed_roles):
            # should not raise
            self.block.is_user_ta(user_id, course_id)

            self.project_api_mock.get_user_roles_for_course.assert_called_once_with(user_id, course_id)

    @ddt.data(
        (1, 'qwe', ['qwe'], ['role1', 'role2']),
        (2, 'asd', [], ['qwe', 'rty']),
        (3, 'course_id', ['role1', 'role2'], ['123', '456']),
    )
    @ddt.unpack
    def test_is_ta_fails(self, user_id, course_id, user_roles, allowed_roles):
        self.project_api_mock.get_user_roles_for_course.return_value = set(user_roles)
        with mock.patch.object(AuthXBlockMixin, 'ta_roles', allowed_roles):
            self.assertFalse(self.block.is_user_ta(user_id, course_id))

    @ddt.data(
        (1, [1, 2], True),
        (17, [17], True),
        (1, [2, 3], False),
        (95, [120, 123], False),
    )
    @ddt.unpack
    def test_is_group_member(self, user_id, group_members, is_member):
        self.user_id_mock.return_value = user_id
        with mock.patch.object(WorkgroupAwareXBlockMixin, 'workgroup', mock.PropertyMock()) as patched_workgroup:
            patched_workgroup.return_value = WorkgroupDetails(id=0, users=[{"id": u_id} for u_id in group_members])

            self.assertEqual(self.block.is_group_member, is_member)

    @ddt.data(
        ({}, False),
        ({'qwe': 'rty'}, False),
        ({UserAwareXBlockMixin.TA_REVIEW_KEY: 1}, True),
        ({UserAwareXBlockMixin.TA_REVIEW_KEY: 15}, True),
    )
    @ddt.unpack
    def test_is_admin_grader(self, preferences, expected_is_admin_grader):
        with mock.patch.object(WorkgroupAwareXBlockMixin, 'user_preferences', mock.PropertyMock()) as patched_prefs:
            patched_prefs.return_value = preferences

            self.assertEqual(self.block.is_admin_grader, expected_is_admin_grader)


class AuthXBlockMixinGuineaPig(AuthXBlockMixin):
    COURSE_ID = 4321

    ALL_ORGS_PERM = "all_orgs_perm"
    SINGLE_ORG_PERM = "single_role_perm"
    TA_PERM = "ta_perm"
    TA_ROLE = "ta_role"

    def __init__(self, project_api):
        self._project_api = project_api

    @property
    def course_id(self):
        return self.COURSE_ID

    @property
    def see_dashboard_for_all_orgs_perms(self):
        return {self.ALL_ORGS_PERM}

    @property
    def ta_roles(self):
        return {self.TA_ROLE}

    @property
    def see_dashboard_ta_perms(self):
        return {self.TA_PERM}

    @property
    def see_dashboard_role_perms(self):
        return {self.SINGLE_ORG_PERM}

    @property
    def project_api(self):
        return self._project_api


@ddt.ddt
class TestAuthXBlockMixin(TestCase, TestWithPatchesMixin):

    USER_ID = 1234

    def setUp(self):
        self.project_api_mock = get_mock_project_api()
        self.block = AuthXBlockMixinGuineaPig(self.project_api_mock)

    def test_outsider_not_allowed(self):
        self.assertFalse(self.block.can_access_dashboard(self.USER_ID))
        self.project_api_mock.get_user_permissions.assert_called_once_with(self.USER_ID)

    @ddt.data(
        ((AuthXBlockMixinGuineaPig.ALL_ORGS_PERM, ), True),
        ((AuthXBlockMixinGuineaPig.ALL_ORGS_PERM, "foo", "bar"), True),
        ((AuthXBlockMixinGuineaPig.SINGLE_ORG_PERM, "foo", "bar"), True),
        (("foo", "bar"), False),
        ([], False),
    )
    @ddt.unpack
    def test_main_org_allowed(self, role_names, allowed):
        group_details = [
            UserGroupDetails(id=idx, name=name)
            for idx, name in enumerate(role_names)
        ]
        self.project_api_mock.get_user_permissions.return_value = group_details
        self.assertEqual(self.block.can_access_dashboard(self.USER_ID), allowed)
        self.project_api_mock.get_user_permissions.assert_called_once_with(self.USER_ID)

    def test_ta_allowed(self):
        self.project_api_mock.get_user_permissions.return_value = [
            UserGroupDetails(id=1, name=AuthXBlockMixinGuineaPig.TA_PERM)
        ]
        self.project_api_mock.get_user_roles_for_course.return_value = {
            AuthXBlockMixinGuineaPig.TA_ROLE
        }
        self.assertTrue(self.block.can_access_dashboard(self.USER_ID))
        self.project_api_mock.get_user_permissions.assert_called_once_with(self.USER_ID)
        self.project_api_mock.get_user_roles_for_course.assert_called_once_with(
            self.USER_ID, self.block.COURSE_ID
        )

    def test_ta_not_allowed(self):
        self.project_api_mock.get_user_permissions.return_value = [
            UserGroupDetails(id=1, name=AuthXBlockMixinGuineaPig.TA_PERM)
        ]
        self.project_api_mock.get_user_roles_for_course.return_value = set()
        self.assertFalse(self.block.can_access_dashboard(self.USER_ID))
        self.project_api_mock.get_user_permissions.assert_called_once_with(self.USER_ID)
        self.project_api_mock.get_user_roles_for_course.assert_called_once_with(
            self.USER_ID, self.block.COURSE_ID
        )


@ddt.ddt
class TestAuthXBlockMixinSettings(TestCase, TestWithPatchesMixin):

    def setUp(self):
        self.block = AuthXBlockMixin()
        self.block._get_setting = mock.MagicMock()

    def test_see_dashboard_ta_perms(self):
        expected = {"foo", "bar"}
        self.block._get_setting.return_value = list(expected)
        self.assertEqual(self.block.see_dashboard_ta_perms, expected)
        self.block._get_setting.assert_called_once_with(
            AuthXBlockMixin.ACCESS_DASHBOARD_TA_PERMS_KEY, []
        )

    def test_see_dashboard_role_perms(self):
        expected = {"foo", "bar"}
        self.block._get_setting.return_value = list(expected)
        self.assertEqual(self.block.see_dashboard_role_perms, expected)
        self.block._get_setting.assert_called_once_with(
            AuthXBlockMixin.ACCESS_DASHBOARD_ROLE_PERMS_KEY, []
        )

    def test_see_dashboard_for_all_orgs_perms(self):
        expected = {"foo", "bar"}
        self.block._get_setting.return_value = list(expected)
        self.assertEqual(self.block.see_dashboard_for_all_orgs_perms, expected)
        self.block._get_setting.assert_called_once_with(
            AuthXBlockMixin.ACCESS_DASHBOARD_FOR_ALL_ORGS_PERMS_KEY, []
        )

    def test_ta_roles(self):
        expected = {"foo", "bar"}
        self.block._get_setting.return_value = list(expected)
        self.assertEqual(self.block.ta_roles, expected)
        self.block._get_setting.assert_called_once_with(
            AuthXBlockMixin.COURSE_ACCESS_TA_ROLES_KEY, AuthXBlockMixin.DEFAULT_TA_ROLE
        )


@ddt.ddt
class TestDashboardRootXBlockMixin(TestCase, TestWithPatchesMixin):
    class DashboardRootXBlockMixinGuineaPig(MockedAuthXBlockMixin, DashboardRootXBlockMixin):
        def __init__(self):
            self._project_details = mock.Mock()

        @property
        def project_details(self):
            return self._project_details

    def setUp(self):
        self.block = self.DashboardRootXBlockMixinGuineaPig()
        self.project_api_mock = get_mock_project_api()
        self.make_patch(
            self.DashboardRootXBlockMixinGuineaPig, 'project_api',
            mock.PropertyMock(return_value=self.project_api_mock)
        )

    @ddt.data(
        [1, 2, 3],
        [4, 5],
        []
    )
    def test_workgroups(self, workgroup_ids):
        def _get_workgroup_by_id(workgroup_id):
            return {"id": workgroup_id, "users": []}

        self.block.project_details.workgroups = workgroup_ids
        self.project_api_mock.get_workgroup_by_id.side_effect = _get_workgroup_by_id

        workgroups = list(self.block.workgroups)

        expected_calls = [mock.call(workgroup_id) for workgroup_id in workgroup_ids]
        expected_groups = [_get_workgroup_by_id(workgroup_id) for workgroup_id in workgroup_ids]
        self.assertEqual(self.project_api_mock.get_workgroup_by_id.mock_calls, expected_calls)
        self.assertEqual(workgroups, expected_groups)

    @ddt.data(
        ([1], [1]),
        ([2], [2, 3]),
        ([1, 2], [1, 2, 3]),
    )
    @ddt.unpack
    def test_users_in_workgroups(self, workgroup_ids, expected_user_ids):
        workgroups = {
            1: WorkgroupDetails(id=1, users=[{'id': 1}]),
            2: WorkgroupDetails(id=2, users=[{'id': 2}, {'id': 3}])
        }

        def _get_workgroup_by_id(workgroup_id):
            return workgroups.get(workgroup_id, None)

        self.block.project_details.workgroups = workgroup_ids
        self.project_api_mock.get_workgroup_by_id.side_effect = _get_workgroup_by_id

        users = self.block.all_users_in_workgroups

        self.assertEqual([user.id for user in users], expected_user_ids)

    def test_add_students_and_workgroups_to_context(self):
        context = {}
        workgroup_value = [
            WorkgroupDetails(id=1, users=[{'id': 1}]),
            WorkgroupDetails(id=2, users=[{'id': 2}, {'id': 3}])
        ]
        users_value = ['user_sentinel']
        self.make_patch(type(self.block), 'workgroups', mock.PropertyMock(return_value=workgroup_value))
        self.make_patch(type(self.block), 'all_users_in_workgroups', mock.PropertyMock(return_value=users_value))

        self.block._add_students_and_workgroups_to_context(context)
        self.assertEqual(context[Constants.TARGET_WORKGROUPS], workgroup_value)
        self.assertEqual(context[Constants.TARGET_STUDENTS], users_value)
        self.assertEqual(context[Constants.FILTERED_STUDENTS], set())

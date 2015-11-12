# pylint:disable=protected-access,no-self-use,invalid-name
from unittest import TestCase
import ddt
import mock

from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
import group_project_v2
from group_project_v2.mixins import ChildrenNavigationXBlockMixin, CourseAwareXBlockMixin, UserAwareXBlockMixin, \
    WorkgroupAwareXBlockMixin
from group_project_v2.project_api import ProjectAPI
from group_project_v2.utils import OutsiderDisallowedError
from tests.utils import TestWithPatchesMixin, raise_api_error
from xblock.core import XBlock
from xblock.runtime import Runtime


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
        self.children_mock = self.make_patch(ChildrenNavigationXBlockMixinGuineaPig, 'children', mock.PropertyMock())
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

        self.assertEqual(self.block.get_child_category(child_with_category), child_with_category.category)
        self.assertEqual(self.block.get_child_category(child_with_plugin_name), child_with_plugin_name.plugin_name)
        self.assertEqual(
            self.block.get_child_category(child_with_plugin_name_and_category),
            child_with_plugin_name_and_category.category
        )
        self.assertEqual(self.block.get_child_category(child_with_no_target_props), None)

    def test_get_children_by_category(self):
        child_categories = {
            'block_1': 'category_1',
            'block_1_2': 'category_1',
            'block_2': 'category_2',
            'block_3': 'category_3'
        }
        self.children_mock.return_value = ['block_1', 'block_1_2', 'block_2', 'block_3']
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
        print id(child1), id(child2)

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
        self.assertEqual(self.block.course_id, unicode(course_id))


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
        self.project_api_mock = mock.create_autospec(ProjectAPI)
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
        self.project_api_mock.get_user_workgroup_for_course.assert_called_once_with(user_id, course_id)

        self.project_api_mock.get_user_preferences.reset_mock()
        self.project_api_mock.get_user_workgroup_for_course.reset_mock()

        self.assertEqual(self.block.workgroup, workgroup)  # checks caching

        self.project_api_mock.get_user_preferences.assert_not_called()
        self.project_api_mock.get_user_workgroup_for_course.assert_not_called()

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

        with mock.patch.object(WorkgroupAwareXBlockMixin, '_confirm_outsider_allowed'):
            # patched_check is noop if everything is ok, so we're letting it return a mock, or whatever it pleases
            self.assertEqual(self.block.workgroup, workgroup)
            self.project_api_mock.get_workgroup_by_id.assert_called_once_with(pref_group_id)

    def test_outsider_disallowed_propagates(self):
        self.project_api_mock.get_user_preferences.return_value = {WorkgroupAwareXBlockMixin.TA_REVIEW_KEY: 1}

        with mock.patch.object(WorkgroupAwareXBlockMixin, '_confirm_outsider_allowed') as patched_check:
            patched_check.side_effect = OutsiderDisallowedError("QWERTY")

            self.assertRaises(OutsiderDisallowedError, lambda: self.block.workgroup)
            patched_check.assert_called_with(self.project_api_mock, self.block.user_id, self.block.course_id)

    @ddt.data(
        (1, 'qwe', ['role1'], ['role1', 'role2']),
        (2, 'asd', ['qwe', 'asd'], ['qwe', 'rty']),
        (3, 'course_id', ['123', '456'], ['123', '456']),
    )
    @ddt.unpack
    def test_confirm_outsider_allowed(self, user_id, course_id, user_roles, allowed_roles):
        self.project_api_mock.get_user_roles_for_course.return_value = [
            {'role': role} for role in user_roles
        ]
        with mock.patch.object(group_project_v2.mixins, 'ALLOWED_OUTSIDER_ROLES', allowed_roles):
            # should not raise
            self.block._confirm_outsider_allowed(self.project_api_mock, user_id, course_id)

            self.project_api_mock.get_user_roles_for_course.assert_called_once_with(user_id, course_id)

    @ddt.data(
        (1, 'qwe', ['qwe'], ['role1', 'role2']),
        (2, 'asd', [], ['qwe', 'rty']),
        (3, 'course_id', ['role1', 'role2'], ['123', '456']),
    )
    @ddt.unpack
    def test_confirm_outsider_allowed_raises(self, user_id, course_id, user_roles, allowed_roles):
        self.project_api_mock.get_user_roles_for_course.return_value = [
            {'role': role} for role in user_roles
        ]
        with mock.patch.object(group_project_v2.mixins, 'ALLOWED_OUTSIDER_ROLES', allowed_roles):
            self.assertRaises(
                OutsiderDisallowedError,
                lambda: self.block._confirm_outsider_allowed(self.project_api_mock, user_id, course_id)
            )

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
            patched_workgroup.return_value = {"id": 'irrelevant', "users": [{"id": u_id} for u_id in group_members]}

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

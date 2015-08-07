from unittest import TestCase
import ddt
import mock

from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
from group_project_v2.mixins import ChildrenNavigationXBlockMixin, CourseAwareXBlockMixin, UserAwareXBlockMixin
from tests.utils import TestWithPatchesMixin
from xblock.core import XBlock
from xblock.runtime import Runtime


def _make_block_mock(block_id, category=None):
    result = mock.create_autospec(XBlock)
    result.usage_id = block_id
    result.category = category if category else 'xblock_category'
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

        self.assertEqual(self.block.get_child_category(child_with_category), child_with_category.category)
        self.assertEqual(self.block.get_child_category(child_with_plugin_name), child_with_plugin_name.plugin_name)
        self.assertEqual(
            self.block.get_child_category(child_with_plugin_name_and_category),
            child_with_plugin_name_and_category.category
        )

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

    def test_get_block_by_id(self):
        actual_block_id = BlockUsageLocator(CourseLocator(org='qwe', course='asd', run='zxc'), 'block_type', '1234')
        string_block_id = unicode(actual_block_id)

        self.block.get_block_by_id(string_block_id)
        self.runtime_mock.get_block.assert_called_with(actual_block_id)


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


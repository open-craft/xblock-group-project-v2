from unittest import TestCase
import ddt
import mock
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
from xblock.core import XBlock
from xblock.field_data import DictFieldData
from xblock.fields import String, ScopeIds
from group_project_v2.utils import FieldValuesContextManager, get_block_content_id


class DummyXBlock(XBlock):
    field = String(values=[10, 15, 20])


@ddt.ddt
class FieldValuesContextManagerTests(TestCase):
    def setUp(self):
        self.runtime_mock = mock.Mock()
        self.block = DummyXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())

    @ddt.data([], [1, 2, 3], range(5))
    def test_context_manager(self, values):
        values_generator = mock.Mock(return_value=values)
        initial_values = self.block.fields['field'].values

        with FieldValuesContextManager(self.block, 'field', values_generator):
            available_values = self.block.fields['field'].values

            self.assertTrue(values_generator.called)
            self.assertEqual(available_values, values)

        self.assertEqual(self.block.fields['field'].values, initial_values)


@ddt.ddt
class TestUtils(TestCase):
    @ddt.data(
        'usage1', 'usage2', 'usage3', 123,
        BlockUsageLocator(CourseLocator(org="org1", course='course1', run='run1'), "bl_type1", "12312313"),
        BlockUsageLocator(CourseLocator(org="org2", course='course2', run='run2'), "bl_type2", "78978978"),
    )
    def test_get_block_content_id(self, usage):
        block = mock.Mock()
        block.scope_ids.usage_id = usage
        self.assertEqual(get_block_content_id(block), unicode(usage))

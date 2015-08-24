from unittest import TestCase
import ddt
import mock
from xblock.core import XBlock
from xblock.field_data import DictFieldData
from xblock.fields import String
from group_project_v2.utils import FieldValuesContextManager


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

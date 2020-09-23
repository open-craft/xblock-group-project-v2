from builtins import str
from builtins import range
from unittest import TestCase
import ddt
import mock
from datetime import datetime

import pytz
from dateutil.tz import tzoffset
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
from xblock.core import XBlock
from xblock.field_data import DictFieldData
from xblock.fields import String
from group_project_v2.utils import FieldValuesContextManager, get_block_content_id, build_date_field


class DummyXBlock(XBlock):
    field = String(values=[10, 15, 20])


@ddt.ddt
class FieldValuesContextManagerTests(TestCase):
    def setUp(self):
        self.runtime_mock = mock.Mock()
        self.block = DummyXBlock(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())

    @ddt.data([], [1, 2, 3], list(range(5)))
    def test_context_manager(self, values):
        # pylint: disable=unsubscriptable-object
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
        self.assertEqual(get_block_content_id(block), str(usage))

    @ddt.data(
        ("2017-01-01T00:00:00", datetime(2017, 1, 1, 0, 0, 0, 0, tzinfo=None)),
        ("2017-01-01T00:00:00Z", datetime(2017, 1, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)),
        ("2016-11-28T14:53:22.763Z", datetime(2016, 11, 28, 14, 53, 22, 763000, tzinfo=pytz.UTC)),
        ("2015-03-09T05:06:07.000001Z", datetime(2015, 3, 9, 5, 6, 7, 1, tzinfo=pytz.UTC)),
        (
            "2015-03-09T05:06:07.123456+08:00",
            datetime(2015, 3, 9, 5, 6, 7, 123456, tzinfo=tzoffset(None, 28800))
        ),
        ("", None),
        ("qwertyuiop", None),
        ("1234567890", None),
        ("1234567890000000", None),  # this one overflows dateutil.parser
    )
    @ddt.unpack
    def test_build_date_field(self, json_string, expected):
        actual = build_date_field(json_string)
        self.assertEqual(actual, expected)

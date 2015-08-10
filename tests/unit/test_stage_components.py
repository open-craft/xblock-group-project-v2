from unittest import TestCase
import ddt
import mock
from xblock.fields import ScopeIds
from xblock.runtime import Runtime
from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_navigator import ProjectNavigatorViewXBlockBase
from group_project_v2.stage import BaseGroupActivityStage
from group_project_v2.stage_components import StaticContentBaseXBlock
from tests.utils import TestWithPatchesMixin


class StageComponentXBlockTestBase(TestCase, TestWithPatchesMixin):
    block_to_test = None

    def setUp(self):
        super(StageComponentXBlockTestBase, self).setUp()
        self.runtime_mock = mock.create_autospec(Runtime)
        self.block = self.block_to_test(self.runtime_mock, field_data={}, scope_ids=mock.Mock())
        self.stage_mock = self.make_patch(self.block_to_test, 'stage', mock.PropertyMock())
        self.fragment_class_mock = mock.Mock()
        patcher = mock.patch('group_project_v2.stage_components.Fragment', self.fragment_class_mock)
        patcher.start()

        self.addCleanup(lambda: patcher.stop())

    def _assert_empty_fragment(self, fragment):
        fragment.add_content.assert_not_called()
        fragment.add_javascript_url.assert_not_called()
        fragment.add_javascript.assert_not_called()
        fragment.add_css_url.assert_not_called()
        fragment.add_css.assert_not_called()
        fragment.add_resources.assert_not_called()


class TestableStaticContentXBlock(StaticContentBaseXBlock):
    TARGET_PROJECT_NAVIGATOR_VIEW = 'some-pn-view'
    TEXT_TEMPLATE = "Static content for {activity_name}"


@ddt.ddt
class TestStaticContentBaseXBlockMixin(StageComponentXBlockTestBase):
    block_to_test = TestableStaticContentXBlock

    def _set_up_navigator(self, activity_name='Activity 1'):
        stage = mock.create_autospec(BaseGroupActivityStage)
        self.stage_mock.return_value = stage

        activity = mock.create_autospec(GroupActivityXBlock)
        activity.display_name = activity_name
        stage.activity = activity

        nav = mock.Mock()
        stage.activity.project.navigator = nav
        return nav

    def test_student_view_no_path_to_navigator(self):
        self.stage_mock.return_value = None
        self._assert_empty_fragment(self.block.student_view({}))

        stage = mock.Mock()
        self.stage_mock.return_value = stage
        stage.activity = None
        self._assert_empty_fragment(self.block.student_view({}))

        stage.activity = mock.Mock()
        stage.activity.project = None
        self._assert_empty_fragment(self.block.student_view({}))

        stage.activity.project = mock.Mock()
        stage.activity.project.navigator = None
        self._assert_empty_fragment(self.block.student_view({}))

    def test_student_view_no_target_block(self):
        navigator_mock = self._set_up_navigator()
        navigator_mock.get_child_of_category = mock.Mock(return_value=None)

        self._assert_empty_fragment(self.block.student_view({}))
        navigator_mock.get_child_of_category.assert_called_once_with(self.block.TARGET_PROJECT_NAVIGATOR_VIEW)

    @ddt.data(
        ({'additional': 'context'}, "Rendered content", "activity 1"),
        ({'other': 'additional'}, "Other content", "Activity 2"),
    )
    @ddt.unpack
    def test_student_view_normal(self, additional_context, content, activity_name):
        target_block = mock.Mock(spec=ProjectNavigatorViewXBlockBase)
        target_block.icon = "I'm icon"
        target_block.scope_ids = mock.create_autospec(spec=ScopeIds)

        navigator_mock = self._set_up_navigator(activity_name)
        navigator_mock.get_child_of_category.return_value = target_block

        with mock.patch('group_project_v2.stage_components.loader.render_template') as patched_render_template, \
                mock.patch('group_project_v2.stage_components.get_link_to_block') as patched_get_link_to_block:
            patched_render_template.return_value = content
            patched_get_link_to_block.return_value = "some link"

            expected_context = {
                'block': self.block,
                'block_link': 'some link',
                'block_text': TestableStaticContentXBlock.TEXT_TEMPLATE.format(activity_name=activity_name),
                'target_block_id': str(target_block.scope_ids.usage_id),
                'view_icon': target_block.icon
            }
            expected_context.update(additional_context)

            fragment = self.block.student_view(additional_context)
            fragment.add_content.assert_called_once_with(content)

            patched_get_link_to_block.assert_called_once_with(target_block)
            patched_render_template.assert_called_once_with(StaticContentBaseXBlock.TEMPLATE_PATH, expected_context)
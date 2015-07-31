""" Base classes for integration tests """
from django.utils.safestring import mark_safe
import mock
from sample_xblocks.basic.content import HtmlBlock
from xblock.core import XBlock
from xblock.fields import String, Scope

from xblockutils.base_test import SeleniumXBlockTest

from group_project_v2.group_project import GroupActivityXBlock
from tests.integration.page_elements import GroupProjectElement
from tests.utils import loader, get_mock_project_api


def get_block_link(block):
    return "/scenario/test/student_view/?student=1&activate_block_id={block_id}".format(
        block_id=block.scope_ids.usage_id
    )


class DummyHtmlXBlock(XBlock):
    data = String(default=u"", scope=Scope.content)

    def student_view(self):
        return mark_safe(self.data)


class BaseIntegrationTest(SeleniumXBlockTest):
    """ Base Integraition test class """
    PROJECT_API_PATCHES = (
        "group_project_v2.project_api.ProjectAPIXBlockMixin.project_api",
    )

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super(BaseIntegrationTest, cls).setUpClass()
        entry_point = mock.Mock(
            dist=mock.Mock(key='xblock'),
            load=mock.Mock(return_value=HtmlBlock),
        )
        entry_point.name = "html"
        cls._extra_entry_points_record = ("html", entry_point)
        XBlock.extra_entry_points.append(cls._extra_entry_points_record)

    @classmethod
    def tearDownClass(cls):  # pylint: disable=invalid-name
        super(BaseIntegrationTest, cls).tearDownClass()
        XBlock.extra_entry_points.remove(cls._extra_entry_points_record)

    def _set_up_global_patches(self):
        patchers = []

        asides_patch = mock.patch(
            "workbench.runtime.WorkbenchRuntime.applicable_aside_types",
            mock.Mock(return_value=[])
        )
        asides_patch.start()
        patchers.append(asides_patch)

        for patch_location in self.PROJECT_API_PATCHES:
            patcher = mock.patch(patch_location, self.project_api_mock)
            patcher.start()
            patchers.append(patcher)

        patch_get_link_to_block_at = (
            'group_project_v2.stage.get_link_to_block',
            'group_project_v2.stage_components.get_link_to_block'
        )
        for location in patch_get_link_to_block_at:
            patcher = mock.patch(location, mock.Mock(side_effect=get_block_link))
            patcher.start()
            patchers.append(patcher)

        return patchers

    def setUp(self):
        """
        Set Up method
        """

        super(BaseIntegrationTest, self).setUp()
        self.project_api_mock = get_mock_project_api()

        patchers = self._set_up_global_patches()

        def cleanup():
            for patcher in patchers:
                patcher.stop()

        self.addCleanup(cleanup)

    def go_to_view(self, view_name='student_view', student_id=1):
        """
        Navigate to the page `page_name`, as listed on the workbench home
        Returns the DOM element on the visited page located by the `css_selector`
        """
        result = super(BaseIntegrationTest, self).go_to_view(view_name, student_id)
        return result

    def load_scenario(self, xml_file, params=None, load_immediately=True):
        """
        Given the name of an XML file in the xml_templates folder, load it into the workbench.
        """
        params = params or {}
        scenario_xml = loader.render_template("xml/{}".format(xml_file), params)
        return self.load_scenario_xml(scenario_xml, load_immediately)

    def load_scenario_xml(self, scenario_xml, load_immediately=True):
        """
        Given the name of an XML file in the xml_templates folder, load it into the workbench.
        """
        self.set_scenario_xml(scenario_xml)
        if load_immediately:
            return self.go_to_view("student_view")

    def get_activities_map(self):
        """
        Builds a map of activity ids to activity names.
        """
        group_project = self.load_root_xblock()
        runtime = group_project.runtime
        children = [runtime.get_block(child_id) for child_id in group_project.children]
        return {
            child.scope_ids.usage_id: child.display_name
            for child in children
            if isinstance(child, GroupActivityXBlock)
        }


class SingleScenarioTestSuite(BaseIntegrationTest):
    """
    Helper class for single scenario tests
    """
    scenario = None
    page = None

    def setUp(self):
        """
        Set Up method
        """
        super(SingleScenarioTestSuite, self).setUp()
        self.load_scenario(self.scenario, load_immediately=False)

    def _prepare_page(self, view_name='student_view', student_id=1):
        """
        Loads scenario page and returns top-level wrapper element
        """
        scenario = self.go_to_view(view_name=view_name, student_id=student_id)
        self.page = GroupProjectElement(self.browser, scenario)

    def _update_after_reload(self):
        top_element = self.browser.find_element_by_css_selector('.workbench .preview > div.xblock-v1:first-child')
        self.page = GroupProjectElement(self.browser, top_element)

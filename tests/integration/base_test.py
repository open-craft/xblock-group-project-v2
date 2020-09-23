""" Base classes for integration tests """
from bok_choy.promise import EmptyPromise
import mock
from sample_xblocks.basic.content import HtmlBlock
from xblock.core import XBlock
from xblock.fragment import Fragment

from xblockutils.base_test import SeleniumXBlockTest

from group_project_v2.group_project import GroupActivityXBlock
from tests.integration.page_elements import GroupProjectElement, StageElement
from tests.utils import loader, get_mock_project_api


def get_block_link(block):
    return "/scenario/test/student_view/?student=1&activate_block_id={block_id}".format(
        block_id=block.scope_ids.usage_id
    )


class DummyDiscussionXBlock(XBlock):
    def student_view(self, _context):  # pylint:disable=no-self-use
        """
        Student view
        """
        return Fragment(u"Discussion XBlock placeholder")


class BaseIntegrationTest(SeleniumXBlockTest):
    """ Base Integraition test class """
    PROJECT_API_PATCHES = (
        "group_project_v2.project_api.ProjectAPIXBlockMixin.project_api",
    )

    activity_id = None
    stage_element = StageElement

    @classmethod
    def _append_entrypoint(cls, category, block_class):
        entry_point = mock.Mock(
            dist=mock.Mock(key='xblock'),
            load=mock.Mock(return_value=block_class),
        )
        entry_point.name = category
        cls._extra_entry_points_records.append((category, entry_point))

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super(BaseIntegrationTest, cls).setUpClass()
        cls._extra_entry_points_records = []
        cls._append_entrypoint('html', HtmlBlock)
        cls._append_entrypoint('discussion-forum', DummyDiscussionXBlock)
        XBlock.extra_entry_points.extend(cls._extra_entry_points_records)

    @classmethod
    def tearDownClass(cls):  # pylint: disable=invalid-name
        super(BaseIntegrationTest, cls).tearDownClass()
        for entry_point in cls._extra_entry_points_records:
            XBlock.extra_entry_points.remove(entry_point)

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
            'group_project_v2.stage.base.get_link_to_block',
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

    # pylint: disable=inconsistent-return-statements
    def load_scenario_xml(self, scenario_xml, load_immediately=True):
        """
        Given the name of an XML file in the xml_templates folder, load it into the workbench.
        """
        self.set_scenario_xml(scenario_xml)
        if load_immediately:
            return self.go_to_view("student_view")

    def get_stage(self, group_project, stage_element_type=None):
        """
        Returns stage element wrapper
        """
        stage_element_type = stage_element_type if stage_element_type else self.stage_element
        stage_element = group_project.activities[0].stages[0]
        self.activity_id = group_project.activities[0].id
        if stage_element_type != StageElement:
            stage_element = stage_element_type(self.browser, stage_element.element)
        self.assertTrue(stage_element.is_displayed())
        return stage_element

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

    def wait_for_ajax(self):
        def _is_ajax_finished():
            """
            Check if all the ajax calls on the current page have completed.
            """
            return self.browser.execute_script("return jQuery.active") == 0

        EmptyPromise(_is_ajax_finished, "Finished waiting for ajax requests.").fulfill()


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

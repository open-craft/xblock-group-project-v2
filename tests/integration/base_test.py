""" Base classes for integration tests """
import textwrap
from django.utils.safestring import mark_safe
import mock
from sample_xblocks.basic.content import HtmlBlock
from xblock.core import XBlock
from xblock.fields import String, Scope

from xblockutils.base_test import SeleniumXBlockTest

from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import ProjectAPIXBlockMixin
from tests.integration.page_elements import GroupProjectElement
from tests.utils import loader, get_mock_project_api


class DummyHtmlXBlock(XBlock):
    data = String(default=u"", scope=Scope.content)

    def student_view(self):
        return mark_safe(self.data)


class BaseIntegrationTest(SeleniumXBlockTest):
    """ Base Integraition test class """
    PROJECT_API_PATCHES = (
        "group_project_v2.mixins.ProjectAPIXBlockMixin",
        "group_project_v2.stage_components.ProjectAPIXBlockMixin",
    )

    @classmethod
    def setUpClass(cls):
        super(BaseIntegrationTest, cls).setUpClass()
        entry_point = mock.Mock(
            dist=mock.Mock(key='xblock'),
            load=mock.Mock(return_value=HtmlBlock),
        )
        entry_point.name = "html"
        cls._extra_entry_points_record = ("html", entry_point)
        XBlock.extra_entry_points.append(cls._extra_entry_points_record)

    @classmethod
    def tearDownClass(cls):
        super(BaseIntegrationTest, cls).tearDownClass()
        XBlock.extra_entry_points.remove(cls._extra_entry_points_record)

    def setUp(self):
        """
        Set Up method
        """

        super(BaseIntegrationTest, self).setUp()
        self.project_api_mock = get_mock_project_api()
        patch = mock.Mock(spec=ProjectAPIXBlockMixin)
        patch.project_api = mock.PropertyMock(return_value=self.project_api_mock)

        patchers = []
        for patch_location in self.PROJECT_API_PATCHES:
            patcher = mock.patch(patch_location, patch)
            patcher.start()
            patchers.append(patcher)

        def stop_patchers():
            for patcher in patchers:
                patcher.stop()

        self.addCleanup(stop_patchers)


    def _add_external_features(self):
        """
        Adds script providing external features to page
        """
        script_url = '/resource/group-project-v2/public/js/test_scripts/external_features.js'
        self.browser.execute_script(textwrap.dedent("""
            var s=window.document.createElement('script');
            s.src='{}';
            window.document.head.appendChild(s);
        """).format(script_url))

    def go_to_view(self, view_name='student_view', student_id=1):
        """
        Navigate to the page `page_name`, as listed on the workbench home
        Returns the DOM element on the visited page located by the `css_selector`
        """
        result = super(BaseIntegrationTest, self).go_to_view(view_name, student_id)
        self._add_external_features()
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

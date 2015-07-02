import textwrap
from selenium.common.exceptions import NoSuchElementException

from xblockutils.base_test import SeleniumXBlockTest

import group_project_v2.project_api as project_api_module
from group_project_v2.group_project import GroupActivityXBlock
from tests.utils import loader, get_mock_project_api


class BaseIntegrationTest(SeleniumXBlockTest):
    """ Base Integraition test class """
    def setUp(self):
        """
        Set Up method
        """
        super(BaseIntegrationTest, self).setUp()
        self.project_api_mock = get_mock_project_api()
        # monkeypatching project_api
        project_api_module.project_api = self.project_api_mock

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
        group_project = self.load_root_xblock()
        runtime = group_project.runtime
        children = [runtime.get_block(child_id) for child_id in group_project.children]
        return {
            child.scope_ids.usage_id: child.display_name
            for child in children
            if isinstance(child, GroupActivityXBlock)
        }


class SingleScenarioTestSuite(BaseIntegrationTest):
    scenario = None

    def setUp(self):
        super(SingleScenarioTestSuite, self).setUp()
        self.load_scenario(self.scenario)

    def _prepare_page(self, view_name='student_view', student_id=1):
        scenario = self.go_to_view(view_name=view_name, student_id=student_id)
        self.page = GroupProjectElement(self.browser, scenario)
        self.activities_map = self.get_activities_map()


class BaseElement(object):
    def __init__(self, browser, element):
        self._browser = browser
        self._element = element

    @property
    def browser(self):
        return self._browser

    @property
    def element(self):
        return self._element

    def __getattr__(self, item):
        if hasattr(self.__dict__, item):
            return getattr(self.__dict__, item)
        if hasattr(self.element, item):
            return getattr(self.element, item)
        return super(BaseElement, self).__getattribute__(item)


class GroupProjectElement(BaseElement):
    """ Wrapper around group project xblock element providing helpers common actions """
    ACTIVITY_CSS_SELECTOR = ".xblock-v1[data-block-type='group-project-v2-activity']"

    @property
    def activities(self):
        elements = self._element.find_elements_by_css_selector(self.ACTIVITY_CSS_SELECTOR)
        return [ActivityElement(self.browser, element) for element in elements]

    def get_activity_by_id(self, activity_id):
        activity_selector = self.ACTIVITY_CSS_SELECTOR+"[data-usage='{}']".format(activity_id)
        activity_element = self._element.find_element_by_css_selector(activity_selector)
        return ActivityElement(self.browser, activity_element)

    def find_stage(self, activity_id, stage_id):
        activity_selector = self.ACTIVITY_CSS_SELECTOR+"[data-usage='{}']".format(activity_id)
        stage_selector = "#activity_"+stage_id
        activity_element = self._element.find_element_by_css_selector(activity_selector)
        return activity_element.find_element_by_css_selector(stage_selector)


class ActivityElement(BaseElement):
    STAGE_CSS_SELECTOR = "div.activity_section"

    @property
    def id(self):
        return self._element.get_attribute('data-usage')

    @property
    def stages(self):
        elements = self._element.find_elements_by_css_selector(self.STAGE_CSS_SELECTOR)
        return [StageElement(self.browser, element) for element in elements]

    def get_stage_by_id(self, stage_id):
        stage_selector = self.STAGE_CSS_SELECTOR + "#activity_"+stage_id
        stage_element = self._element.find_element_by_css_selector(stage_selector)
        return StageElement(self.browser, stage_element)


class StageElement(BaseElement):
    @property
    def id(self):
        return self._element.get_attribute('id').replace('activity_', '')

    @property
    def title(self):
        return self._element.find_element_by_css_selector('h1 .stage_title').text

    @property
    def open_close_label(self):
        try:
            element = self._element.find_element_by_css_selector('h1 .highlight')
            return element.text
        except NoSuchElementException:
            return None

    @property
    def content(self):
        return self._element.find_element_by_css_selector('.stage_content')

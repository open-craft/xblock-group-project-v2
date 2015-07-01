from mock import Mock

from xblockutils.base_test import SeleniumXBlockTest

import group_project_v2.project_api as project_api_module
from tests.utils import loader


class BaseIntegrationTest(SeleniumXBlockTest):
    def setUp(self):
        # monkeypatching project_api
        project_api_module.project_api = Mock(spec=project_api_module.ProjectAPI)

    def load_scenario(self, xml_file, params=None, load_immediately=True):
        """
        Given the name of an XML file in the xml_templates folder, load it into the workbench.
        """
        params = params or {}
        scenario = loader.render_template("xml/{}".format(xml_file), params)
        self.set_scenario_xml(scenario)
        if load_immediately:
            return self.go_to_view("student_view")
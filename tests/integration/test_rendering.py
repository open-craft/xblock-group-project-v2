from selenium.common.exceptions import NoSuchElementException
from tests.integration.base_test import SingleScenarioTestSuite


class TestRendering(SingleScenarioTestSuite):
    scenario = "example_1.xml"

    def test_initial_state(self):
        expected_visible_stages = {
            "Activity 1": "overview",
            "Activity 2": "group_assessment"
        }

        for activity_name, stage_id in expected_visible_stages.iteritems():
            activity_id = self.stages_map[activity_name]
            stage_element = self.page.find_stage(activity_id, stage_id)
            self.assertTrue(stage_element.is_displayed())

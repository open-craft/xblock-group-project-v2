"""
High level rendering tests
"""
import logging
from tests.integration.base_test import SingleScenarioTestSuite

log = logging.getLogger(__name__)

class TestGeneralFunctionality(SingleScenarioTestSuite):
    scenario = "example_1.xml"

    def test_initial_stage_visibility(self):
        self._prepare_page()

        expected_visible_stage_title = "Overview"  # should show first not completed

        self.assertEqual(len(self.page.activities), 1)
        self.assertEqual(len(self.page.activities[0].stages), 1)

        stage = self.page.activities[0].stages[0]
        self.assertTrue(stage.is_displayed())
        self.assertEqual(stage.title, expected_visible_stage_title)
        self.assertEqual(stage.content.text, "I'm Overview Stage")
        self.assertEqual(stage.open_close_label, None)

        selected_stage = self.page.project_navigator.selected_stage
        self.assertEqual(selected_stage.title, expected_visible_stage_title)

"""
High level rendering tests
"""
import logging
from tests.integration.base_test import SingleScenarioTestSuite
from tests.utils import XMLContents, get_open_close_label

log = logging.getLogger(__name__)


class TestRendering(SingleScenarioTestSuite):
    scenario = "example_1.xml"

    def test_initial_stage_visibility(self):
        self._prepare_page()

        expected_visible_stage_title = "Overview"  # should show first not completed

        self.assertEqual(len(self.page.activities), 1)
        self.assertEqual(len(self.page.activities[0].stages), 1)

        stage = self.page.activities[0].stages[0]
        self.assertTrue(stage.is_displayed())
        self.assertEqual(stage.title, expected_visible_stage_title)
        stage_data = XMLContents.Example1.STAGE_DATA[stage.title]

        self.assertEqual(stage.content.text, stage_data['contents'])
        self.assertEqual(
            stage.open_close_label,
            get_open_close_label(stage_data.get('open_date', None), stage_data.get('close_date', None))
        )

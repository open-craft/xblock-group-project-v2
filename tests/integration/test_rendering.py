from tests.integration.base_test import SingleScenarioTestSuite, ActivityElement
from tests.utils import XMLContents, get_open_close_label


class TestRendering(SingleScenarioTestSuite):
    scenario = "example_1.xml"

    def test_initial_stage_visibility(self):
        self._prepare_page()

        expected_visible_stages = {
            "Activity 1": "overview",
            "Activity 2": "group_assessment"
        }

        for activity in self.page.activities:
            activity_name = self.activities_map[activity.id]
            visible_stage_id = expected_visible_stages[activity_name]

            for stage in activity.stages:
                assertion = self.assertTrue if stage.id == visible_stage_id else self.assertFalse
                assertion(stage.is_displayed())

    def test_initial_stage_contents(self):
        self._prepare_page()

        # For test purity, can't rely on navigation features to display other stages.
        self.browser.execute_script("$('.activity_stage').show();")

        for activity in self.page.activities:
            for stage in activity.stages:
                self.assertTrue(stage.is_displayed())  # precondition check - we just made them all visible

                stage_data = XMLContents.Example1.STAGE_DATA[stage.id]
                self.assertEqual(stage_data.title, stage_data['title'])
                self.assertEqual(
                    stage_data.open_close_label,
                    get_open_close_label(stage_data['open_date'], stage_data['open_date'])
                )

                if stage_data['contents'] and stage_data['contents'] != XMLContents.COMPLEX_CONTENTS_SENTINEL:
                    self.assertEqual(stage.content.get_attribute('innerHtml'), stage_data['contents'])


from tests.integration.base_test import SingleScenarioTestSuite, ActivityElement


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

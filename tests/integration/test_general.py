"""
High level rendering tests
"""
from collections import defaultdict
import logging
import mock
from tests.integration.base_test import SingleScenarioTestSuite

log = logging.getLogger(__name__)


class StageStateRegistry(object):
    def __init__(self):
        self._stage_states = defaultdict(list)

    def mark_as_complete(self, course_id, content_id, user_id, stage_id):
        self._stage_states[(course_id, content_id, stage_id)].append(user_id)

    def get_stage_state(self, course_id, content_id, stage_id):
        return self._stage_states[(course_id, content_id, stage_id)]


class TestGeneralFunctionality(SingleScenarioTestSuite):
    scenario = "example_1.xml"
    
    def setUp(self):
        super(TestGeneralFunctionality, self).setUp()
        stage_state_registry = StageStateRegistry()
        self.project_api_mock.get_stage_state = mock.Mock(side_effect=stage_state_registry.get_stage_state)
        self.project_api_mock.mark_as_complete = mock.Mock(side_effect=stage_state_registry.mark_as_complete)

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

import ddt

from group_project_v2.project_api.dtos import CompletionDetails
from group_project_v2.stage import BaseGroupActivityStage
from group_project_v2.stage.mixins import SimpleCompletionStageMixin
from tests.unit.test_stages.base import BaseStageTest

__author__ = 'e.kolpakov'


@ddt.ddt
class TestSimpleCompletionStageMixin(BaseStageTest):
    class SimpleCompletionGuineaPig(SimpleCompletionStageMixin, BaseGroupActivityStage):
        pass

    block_to_test = SimpleCompletionGuineaPig

    @ddt.data(
        ({1}, {1}),
        (set(), set()),
        ({1, 2, 3, 4}, {1, 2, 3, 4}),
        ({1, 4, 11, 92}, {1, 4, 11, 92}),
    )
    @ddt.unpack
    def test_get_users_completion(self, completed_users, expected_completed_users):
        self.project_api_mock.get_completions_by_content_id.return_value = [
            CompletionDetails(user_id=uid) for uid in completed_users
        ]

        completed, partially = self.block.get_users_completion('irrelevant', 'irrelevant')
        self.assertEqual(completed, expected_completed_users)
        self.assertEqual(partially, set())
        self.project_api_mock.get_completions_by_content_id.assert_called_once_with(
            self.block.course_id, self.block.content_id
        )

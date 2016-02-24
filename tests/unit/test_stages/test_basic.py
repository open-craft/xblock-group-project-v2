from group_project_v2.stage import SubmissionStage
from tests.unit.test_stages.base import BaseStageTest


class TestSubmissionStage(BaseStageTest):
    block_to_test = SubmissionStage

    def test_is_graded_stage(self):
        self.assertEqual(self.block.is_graded_stage, True)

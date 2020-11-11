from group_project_v2.stage.base import BaseGroupActivityStage
from group_project_v2.stage.basic import BasicStage, CompletionStage, SubmissionStage
from group_project_v2.stage.feedback_review import EvaluationDisplayStage, GradeDisplayStage
from group_project_v2.stage.review import PeerReviewStage, TeamEvaluationStage

STAGE_TYPES = (
    BasicStage.CATEGORY,
    CompletionStage.CATEGORY,
    SubmissionStage.CATEGORY,
    TeamEvaluationStage.CATEGORY,
    PeerReviewStage.CATEGORY,
    EvaluationDisplayStage.CATEGORY,
    GradeDisplayStage.CATEGORY
)

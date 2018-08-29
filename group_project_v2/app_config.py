BLOCKS = {
    'gp-v2-project': 'group_project_v2.group_project:GroupProjectXBlock',
    'gp-v2-activity': 'group_project_v2.group_project:GroupActivityXBlock',

    'gp-v2-stage-basic': 'group_project_v2.stage:BasicStage',
    'gp-v2-stage-completion': 'group_project_v2.stage:CompletionStage',
    'gp-v2-stage-submission': 'group_project_v2.stage:SubmissionStage',
    'gp-v2-stage-team-evaluation': 'group_project_v2.stage:TeamEvaluationStage',
    'gp-v2-stage-peer-review': 'group_project_v2.stage:PeerReviewStage',
    'gp-v2-stage-evaluation-display': 'group_project_v2.stage:EvaluationDisplayStage',
    'gp-v2-stage-grade-display': 'group_project_v2.stage:GradeDisplayStage',

    'gp-v2-resource': 'group_project_v2.stage_components:GroupProjectResourceXBlock',
    'gp-v2-video-resource': 'group_project_v2.stage_components:GroupProjectVideoResourceXBlock',
    'gp-v2-submission': 'group_project_v2.stage_components:GroupProjectSubmissionXBlock',
    'gp-v2-peer-selector': 'group_project_v2.stage_components:PeerSelectorXBlock',
    'gp-v2-group-selector': 'group_project_v2.stage_components:GroupSelectorXBlock',
    'gp-v2-review-question': 'group_project_v2.stage_components:GroupProjectReviewQuestionXBlock',
    'gp-v2-peer-assessment': 'group_project_v2.stage_components:GroupProjectTeamEvaluationDisplayXBlock',
    'gp-v2-group-assessment': 'group_project_v2.stage_components:GroupProjectGradeEvaluationDisplayXBlock',
    'gp-v2-static-submissions': 'group_project_v2.stage_components:SubmissionsStaticContentXBlock',
    'gp-v2-static-grade-rubric': 'group_project_v2.stage_components:GradeRubricStaticContentXBlock',
    'gp-v2-project-team': 'group_project_v2.stage_components:ProjectTeamXBlock',

    'gp-v2-navigator': 'group_project_v2.project_navigator:GroupProjectNavigatorXBlock',
    'gp-v2-navigator-navigation': 'group_project_v2.project_navigator:NavigationViewXBlock',
    'gp-v2-navigator-resources': 'group_project_v2.project_navigator:ResourcesViewXBlock',
    'gp-v2-navigator-submissions': 'group_project_v2.project_navigator:SubmissionsViewXBlock',
    'gp-v2-navigator-ask-ta': 'group_project_v2.project_navigator:AskTAViewXBlock',
    'gp-v2-navigator-private-discussion': 'group_project_v2.project_navigator:PrivateDiscussionViewXBlock',
}

ENTRYPOINTS = [
    "{entrypoint} = {class_location}".format(entrypoint=entrypoint, class_location=class_location)
    for entrypoint, class_location in BLOCKS.items()
]

PROGRESS_DETACHED_CATEGORIES = list(BLOCKS.keys())

# -*- coding: utf-8 -*-

# Imports ###########################################################

import os
from setuptools import setup


# Functions #########################################################

def package_data(pkg, root_list):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for root in root_list:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

BLOCKS = [
    'gp-v2-project = group_project_v2.group_project:GroupProjectXBlock',

    'gp-v2-activity = group_project_v2.group_project:GroupActivityXBlock',

    'gp-v2-stage-basic = group_project_v2.stage:BasicStage',
    'gp-v2-stage-completion = group_project_v2.stage:CompletionStage',
    'gp-v2-stage-submission = group_project_v2.stage:SubmissionStage',
    'gp-v2-stage-team-evaluation = group_project_v2.stage:TeamEvaluationStage',
    'gp-v2-stage-peer-review = group_project_v2.stage:PeerReviewStage',
    'gp-v2-stage-evaluation-display = group_project_v2.stage:EvaluationDisplayStage',
    'gp-v2-stage-grade-display = group_project_v2.stage:GradeDisplayStage',

    'gp-v2-resource = group_project_v2.stage_components:GroupProjectResourceXBlock',
    'gp-v2-video-resource = group_project_v2.stage_components:GroupProjectVideoResourceXBlock',
    'gp-v2-submission = group_project_v2.stage_components:GroupProjectSubmissionXBlock',
    'gp-v2-peer-selector = group_project_v2.stage_components:PeerSelectorXBlock',
    'gp-v2-group-selector = group_project_v2.stage_components:GroupSelectorXBlock',
    'gp-v2-review-question = group_project_v2.stage_components:GroupProjectReviewQuestionXBlock',
    'gp-v2-peer-assessment = group_project_v2.stage_components:GroupProjectPeerAssessmentXBlock',
    'gp-v2-group-assessment = group_project_v2.stage_components:GroupProjectGroupAssessmentXBlock',
    "gp-v2-static-submissions = group_project_v2.stage_components:SubmissionsStaticContentXBlock",
    "gp-v2-static-grade-rubric = group_project_v2.stage_components:GradeRubricStaticContentXBlock",

    'gp-v2-navigator = group_project_v2.project_navigator:GroupProjectNavigatorXBlock',
    'gp-v2-navigator-navigation = group_project_v2.project_navigator:NavigationViewXBlock',
    'gp-v2-navigator-resources = group_project_v2.project_navigator:ResourcesViewXBlock',
    'gp-v2-navigator-submissions = group_project_v2.project_navigator:SubmissionsViewXBlock',
    'gp-v2-navigator-ask-ta = group_project_v2.project_navigator:AskTAViewXBlock',
]


# Main ##############################################################

setup(
    name='xblock-group-project-v2',
    version='0.3',
    description='XBlock - Group Project V2',
    packages=['group_project_v2'],
    install_requires=[
        'XBlock',
        'xblock-utils',
    ],
    entry_points={
        'xblock.v1': BLOCKS
    },
    package_data=package_data("group_project_v2", ["templates", "public", "res"]),
)

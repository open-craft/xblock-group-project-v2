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
    'group-project-v2 = group_project_v2:GroupProjectXBlock',
    'group-project-v2-activity = group_project_v2:GroupActivityXBlock',
    'group-project-v2-navigator = group_project_v2.components.project_navigator:GroupProjectNavigatorXBlock',
    'group-project-v2-navigator-navigation = group_project_v2.components.project_navigator:NavigationViewXBlock',
    'group-project-v2-navigator-resources = group_project_v2.components.project_navigator:ResourcesViewXBlock',
    'group-project-v2-navigator-submissions = group_project_v2.components.project_navigator:SubmissionsViewXBlock',
    'group-project-v2-navigator-ask-ta = group_project_v2.components.project_navigator:AskTAViewXBlock',
]


# Main ##############################################################

setup(
    name='xblock-group-project-v2',
    version='0.2',
    description='XBlock - Group Project V2',
    packages=['group_project_v2'],
    install_requires=[
        'XBlock',
        'xblock-utils',
    ],
    entry_points={
        'xblock.v1': BLOCKS
    },
    package_data=package_data("group_project_v2", ["static", "templates", "public", "res"]),
)

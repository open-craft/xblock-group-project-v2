# -*- coding: utf-8 -*-

# Imports ###########################################################

import os
from setuptools import setup
from group_project_v2.app_config import ENTRYPOINTS


# Functions #########################################################

def package_data(pkg, root_list):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for root in root_list:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


# Main ##############################################################

setup(
    name='xblock-group-project-v2',
    version='0.4.1',
    description='XBlock - Group Project V2',
    packages=['group_project_v2'],
    install_requires=[
        'XBlock',
        'xblock-utils',
        'django-upload-validator'
    ],
    entry_points={
        'xblock.v1': ENTRYPOINTS
    },
    dependency_links = [
        'https://github.com/mckinseyacademy/django-upload-validator/tarball/b7152b63af6698116337def90a3e6f42ccc06f81#egg=django-upload-validator-0.1.0'
    ],
    package_data=package_data("group_project_v2", ["templates", "public"]),
)

# -*- coding: utf-8 -*-

# Imports ###########################################################

import os

from setuptools import find_packages, setup

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
    version='0.12.8',
    description='XBlock - Group Project V2',
    packages=find_packages(),
    install_requires=[
        'Django>=1.11,<2.3',
        'lazy>=1.1',
        'python-dateutil>=2.1,<3.0',
        'WebOb>=1.6,<2.0',
        'pytz',
        'XBlock>=1.2.2',
        'web-fragments==0.3.2',
        'xblock-utils>=0.9',
        'django-upload-validator==1.0.2',
        'edx-opaque-keys>=0.4',
        'boto>=2.1.0',
        'boto3==1.4.8',
        'google-compute-engine==2.8.13',
        'django-storages==1.8'
    ],
    entry_points={
        'xblock.v1': ENTRYPOINTS
    },
    dependency_links=[
        'https://github.com/edx/xblock-utils/tarball/v1.0.5#egg=xblock-utils-1.0.5',
        'https://github.com/mckinseyacademy/django-upload-validator/tarball/v1.0.2#egg=django-upload-validator-1.0.2'
    ],
    package_data=package_data("group_project_v2", ["templates", "public"]),
)

# -*- coding: utf-8 -*-

# Imports ###########################################################

import os
from setuptools import setup, find_packages
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
    version='0.4.11',
    description='XBlock - Group Project V2',
    packages=find_packages(),
    install_requires=[
        'Django>=1.8,<2.0',
        'lazy>=1.1',
        'python-dateutil>=2.1,<3.0',
        'WebOb>=1.6,<2.0',
        'pytz',
        'XBlock>=1.2.2,<2.0',
        'xblock-utils>=0.9',
        'edx-opaque-keys>=0.4'
    ],
    entry_points={
        'xblock.v1': ENTRYPOINTS
    },
    dependency_links = [
        'https://github.com/edx/xblock-utils/tarball/v1.0.5#egg=xblock-utils-1.0.5',
        'https://github.com/mckinseyacademy/django-upload-validator/tarball/v1.0.2#egg=django-upload-validator==v1.0.2'
    ],
    package_data=package_data("group_project_v2", ["templates", "public"]),
)

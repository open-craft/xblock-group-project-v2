# -*- coding: utf-8 -*-
#

# Imports ###########################################################

import logging
import textwrap
import json
import webob
from lxml import etree
from xml.etree import ElementTree as ET

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict, Float
from xblock.fragment import Fragment

from StringIO import StringIO

from .utils import render_template, AttrDict, load_resource


# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

class GroupProjectBlock(XBlock):
    """
    XBlock providing a video player for videos hosted on Brightcove
    """
    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Group Project"
    )

    weight = Float(
        display_name="Weight",
        help="This is the maximum score that the user receives when he/she successfully completes the problem",
        scope=Scope.settings,
        default=1
    )

    data = String(
        display_name="Drag and Drop",
        help="XML contents to display for this module",
        scope=Scope.content,
        default=textwrap.dedent("""
            <group_project schema_version='1'>


            </group_project>
        """
        ))

    has_score = True

    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        xmltree = etree.fromstring(self.data)

        context = {
        }

        fragment = Fragment()
        fragment.add_content(render_template('/templates/html/group_project.html', context))
        fragment.add_css(load_resource('public/css/group_project.css'))
        fragment.add_javascript(load_resource('public/js/group_project.js'))

        fragment.initialize_js('GroupProjectBlock')

        return fragment

    def studio_view(self, context):
        """
        Editing view in Studio
        """
        fragment = Fragment()
        fragment.add_content(render_template('/templates/html/group_project_edit.html', {
            'self': self,
        }))
        fragment.add_javascript(load_resource('public/js/group_project_edit.js'))

        fragment.initialize_js('GroupProjectEditBlock')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):

        self.display_name = submissions['display_name']
        xml_content = submissions['data']
        max_score = submissions['max_score']

        if not max_score:
            # empty = default
            max_score = 1
        else:
            try:
                # not an integer, then default
                max_score = int(max_score)
            except:
                max_score = 1

        self.weight = max_score

        try:
            etree.parse(StringIO(xml_content))
            self.data = xml_content
        except etree.XMLSyntaxError as e:
            return {
                'result': 'error',
                'message': e.message
            }

        return {
            'result': 'success',
        }

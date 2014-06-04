# -*- coding: utf-8 -*-
#

# Imports ###########################################################

import logging
import textwrap
import json
import webob
from lxml import etree
from xml.etree import ElementTree as ET
from pkg_resources import resource_filename

from django.utils.translation import ugettext as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict, Float
from xblock.fragment import Fragment

from StringIO import StringIO

from .utils import render_template, AttrDict, load_resource

from .group_activity import GroupActivity


# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

class GroupProjectBlock(XBlock):
    """
    XBlock providing a group activity project for a group of students to collaborate upon
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

    item_state = Dict(
        help="JSON payload for assessment values",
        scope=Scope.user_state
    )

    with open (resource_filename(__name__, 'res/default.xml'), "r") as default_xml_file:
        default_xml = default_xml_file.read()

    data = String(
        display_name="",
        help="XML contents to display for this module",
        scope=Scope.content,
        default=textwrap.dedent(default_xml)
    )

    has_score = True

    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        group_activity = GroupActivity.import_xml_string(self.data)
        # TODO: Replace with workgroup call to get real workgroup
        team_members = [
            {
                "name": "Andy Parsons",
                "id": 1,
                "img": "/image/empty_avatar.png"
            },
            {
                "name": "Jennifer Gormley",
                "id": 2,
                "img": "/image/empty_avatar.png"
            },
            {
                "name": "Vishal Ghandi",
                "id": 3,
                "img": "/image/empty_avatar.png"
            }
        ]

        # TODO: Replace with workgroup call to get assigned workgroups
        assess_groups = [
            {
                "id": 101,
                "img": "/image/empty_avatar.png"
            },
            {
                "id": 102,
                "img": "/image/empty_avatar.png"
            },
            {
                "id": 103,
                "img": "/image/empty_avatar.png"
            }
        ]

        context = {
            "group_activity": group_activity,
            "team_members": json.dumps(team_members),
            "assess_groups": json.dumps(assess_groups),
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

    @XBlock.json_handler
    def student_submit_peer_feedback(self, submissions, suffix=''):
        try:
            peer_id = submissions["peer_id"]
            del submissions["peer_id"]

            print "Peer Review for {}: {}".format(peer_id, submissions)

            # Then something like this needs to happen

            # user_id = get_user_id_for_this_session() # ???
            # project_id = get_xblock_id_for_this_session()
            # api_manager.save_data_for_peer(user_id, peer_id, submissions)

            # or

            # for k,v in iteritems(submissions):
            #     api_manager.save_data_for_peer(user_id, peer_id, k, v)

        except Exception as e:
            return {
                'result': 'error',
                'message': e.message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

    @XBlock.json_handler
    def student_submit_other_group_feedback(self, submissions, suffix=''):
        try:
            group_id = submissions["group_id"]
            del submissions["group_id"]

            print "Group Review for {}: {}".format(group_id, submissions)

            # Then something like this needs to happen

            # user_id = get_user_id_for_this_session() # ???
            # project_id = get_xblock_id_for_this_session()
            # api_manager.save_data_for_group(user_id, group_id, submissions)

            # or

            # for k,v in iteritems(submissions):
            #     api_manager.save_data_for_group(user_id, group_id, k, v)

        except Exception as e:
            return {
                'result': 'error',
                'msg': e.message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

# -*- coding: utf-8 -*-
#

# Imports ###########################################################

import logging
import textwrap
import json
import webob
from datetime import datetime, timedelta
import pytz

from lxml import etree
from xml.etree import ElementTree as ET
from pkg_resources import resource_filename

from django.conf import settings
from django.utils import html
from django.utils.translation import ugettext as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict, Float, Integer
from xblock.fragment import Fragment

from StringIO import StringIO

from .utils import render_template, AttrDict, load_resource

from .group_activity import GroupActivity
from .project_api import ProjectAPI
from .upload_file import UploadFile
from .api_error import ApiError

ALLOWED_OUTSIDER_ROLES = getattr(settings, "ALLOWED_OUTSIDER_ROLES", None)
if ALLOWED_OUTSIDER_ROLES is None:
    ALLOWED_OUTSIDER_ROLES = ["assistant"]

try:
    from edx_notifications.data import NotificationMessage
except:
    # Notifications is an optional runtime configuration, so it may not be available for import
    pass

# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

def make_key(*args):
    return ":".join([str(a) for a in args])


class OutsiderDisallowedError(Exception):
    def __init__(self, detail):
        self.value = detail
        super(OutsiderDisallowedError, self).__init__()

    def __str__(self):
        return "Outsider Denied Access: {}".format(self.value)

    def __unicode__(self):
        return u"Outsider Denied Access: {}".format(self.value)


@XBlock.wants('notifications')
@XBlock.wants('courseware_parent_info')
class GroupActivityXBlock(XBlock):
    """
    XBlock providing a group activity project for a group of students to collaborate upon
    """
    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Group Project V2"
    )

    weight = Float(
        display_name="Weight",
        help="This is the maximum score that the user receives when he/she successfully completes the problem",
        scope=Scope.settings,
        default=100.0
    )

    group_reviews_required_count = Integer(
        display_name="Reviews Required Minimum",
        help="The minimum number of group-reviews that should be applied to a set of submissions "
             "(set to 0 to be 'TA Graded')",
        scope=Scope.settings,
        default=3
    )

    user_review_count = Integer(
        display_name="User Reviews Required Minimum",
        help="The minimum number of other-group reviews that an individual user should perform",
        scope=Scope.settings,
        default=1
    )

    item_state = Dict(
        help="JSON payload for assessment values",
        scope=Scope.user_state
    )

    with open(resource_filename(__name__, 'res/default.xml'), "r") as default_xml_file:
        default_xml = default_xml_file.read()

    data = String(
        display_name="",
        help="XML contents to display for this module",
        scope=Scope.content,
        default=textwrap.dedent(default_xml)
    )

    has_score = True

    _project_api = None

    def _confirm_outsider_allowed(self):
        granted_roles = [r["role"] for r in self.project_api.get_user_roles_for_course(self.user_id, self.course_id)]
        for allowed_role in ALLOWED_OUTSIDER_ROLES:
            if allowed_role in granted_roles:
                return True

        raise OutsiderDisallowedError("User does not have an allowed role")

    _known_real_user_ids = {}

    def real_user_id(self, anonymous_student_id):
        if anonymous_student_id not in self._known_real_user_ids:
            self._known_real_user_ids[anonymous_student_id] = self.xmodule_runtime.get_real_user(
                anonymous_student_id).id
        return self._known_real_user_ids[anonymous_student_id]

    @property  # lazy
    def project_api(self):
        if self._project_api is None:
            # Looks like it's an issue, but technically it's not; this code runs in LMS, so 127.0.0.1 is always correct
            # location for API server, as it's basically executed in a neighbour thread/process/whatever.
            api_server = "http://127.0.0.1:8000"
            if hasattr(settings, 'API_LOOPBACK_ADDRESS'):
                api_server = settings.API_LOOPBACK_ADDRESS
            self._project_api = ProjectAPI(api_server)
        return self._project_api

    @property
    def user_id(self):
        try:
            return self.real_user_id(self.xmodule_runtime.anonymous_student_id)
        except:
            return None

    _workgroup = None

    @property  # lazy
    def workgroup(self):
        if self._workgroup is None:
            try:
                user_prefs = self.project_api.get_user_preferences(self.user_id)

                if "TA_REVIEW_WORKGROUP" in user_prefs:
                    self._confirm_outsider_allowed()
                    self._workgroup = self.project_api.get_workgroup_by_id(user_prefs["TA_REVIEW_WORKGROUP"])
                else:
                    self._workgroup = self.project_api.get_user_workgroup_for_course(
                        self.user_id,
                        self.course_id
                    )
            except OutsiderDisallowedError:
                raise
            except:
                self._workgroup = {
                    "id": "0",
                    "users": [],
                }

        return self._workgroup

    @property
    def is_group_member(self):
        return self.user_id in [u["id"] for u in self.workgroup["users"]]

    @property
    def is_admin_grader(self):
        return not self.is_group_member

    @property
    def content_id(self):
        try:
            return unicode(self.scope_ids.usage_id)
        except:
            return self.id

    @property
    def course_id(self):
        try:
            return unicode(self.xmodule_runtime.course_id)
        except:
            return self.xmodule_runtime.course_id

    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        try:
            workgroup = self.workgroup
        except OutsiderDisallowedError as ode:
            error_fragment = Fragment()
            error_fragment.add_content(
                render_template('/templates/html/loading_error.html', {'error_message': unicode(ode)}))
            error_fragment.add_javascript(load_resource('public/js/group_project_error.js'))
            error_fragment.initialize_js('GroupProjectError')
            return error_fragment

        user_id = self.user_id
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

        try:
            group_activity.update_submission_data(
                self.project_api.get_latest_workgroup_submissions_by_id(workgroup["id"])
            )
        except:
            pass

        if self.is_group_member:
            try:
                team_members = [
                    self.project_api.get_user_details(team_member["id"])
                    for team_member in workgroup["users"]
                    if user_id != int(team_member["id"])
                ]
            except:
                team_members = []

            try:
                assess_groups = self.project_api.get_workgroups_to_review(user_id, self.course_id, self.content_id)
            except:
                assess_groups = []
        else:
            team_members = []
            assess_groups = [workgroup]

        context = {
            "group_activity": group_activity,
            "team_members": json.dumps(team_members),
            "assess_groups": json.dumps(assess_groups),
            "ta_graded": (self.group_reviews_required_count < 1),
        }

        fragment = Fragment()
        fragment.add_content(
            render_template('/templates/html/group_project.html', context))
        fragment.add_css(load_resource('public/css/group_project.css'))

        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/vendor/jquery.ui.widget.js'))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/vendor/jquery.fileupload.js'))
        fragment.add_javascript_url(
            self.runtime.local_resource_url(self, 'public/js/vendor/jquery.iframe-transport.js'))

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
        fragment.add_css(load_resource('public/css/group_project_edit.css'))

        fragment.add_javascript(
            load_resource('public/js/group_project_edit.js'))

        fragment.initialize_js('GroupProjectEditBlock')

        return fragment

    def assign_grade_to_group(self, group_id, grade_value):
        self.project_api.set_group_grade(
            group_id,
            self.course_id,
            self.content_id,
            grade_value,
            self.weight
        )
        # Emit analytics event...
        self.runtime.publish(
            self,
            "group_activity.final_grade",
            {
                "grade_value": grade_value,
                "group_id": group_id,
                "content_id": self.content_id,
            }
        )
        notifications_service = self.runtime.service(self, 'notifications')
        if notifications_service:
            self.fire_grades_posted_notification(group_id, notifications_service)

    def calculate_grade(self, group_id):

        def mean(value_array):
            numeric_values = [float(v) for v in value_array]
            return float(sum(numeric_values) / len(numeric_values))

        review_item_data = self.project_api.get_workgroup_review_items_for_group(group_id, self.content_id)
        review_item_map = {
            make_key(review_item['question'], self.real_user_id(review_item['reviewer'])): review_item['answer']
            for review_item in review_item_data
        }
        all_reviewer_ids = set([self.real_user_id(review_item['reviewer']) for review_item in review_item_data])
        group_reviewer_ids = [user["id"] for user in self.project_api.get_workgroup_reviewers(group_id)]
        admin_reviewer_ids = [reviewer_id for reviewer_id in all_reviewer_ids if reviewer_id not in group_reviewer_ids]

        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

        def get_user_grade_value_list(user_id):
            user_grades = []
            for question_id in group_activity.grade_questions:
                user_value = review_item_map.get(make_key(question_id, user_id), None)
                if user_value is None:
                    # if any are incomplete, we consider the whole set to be unusable
                    return None
                else:
                    user_grades.append(user_value)

            return user_grades

        admin_provided_grades = None
        if len(admin_reviewer_ids) > 0:
            admin_provided_grades = []
            # Only include complete admin gradesets
            admin_reviewer_grades = [
                arg
                for arg in [get_user_grade_value_list(admin_id) for admin_id in admin_reviewer_ids]
                if arg
            ]
            admin_grader_count = len(admin_reviewer_grades)
            if admin_grader_count > 1:
                for idx in range(len(group_activity.grade_questions)):
                    admin_provided_grades.append(mean([adm[idx] for adm in admin_reviewer_grades]))
            elif admin_grader_count > 0:  # which actually means admin_grader_count == 1
                admin_provided_grades = admin_reviewer_grades[0]

        user_grades = {}
        if len(group_reviewer_ids) > 0:
            for reviewer_id in group_reviewer_ids:
                this_reviewers_grades = get_user_grade_value_list(reviewer_id)
                if this_reviewers_grades is None:
                    if admin_provided_grades:
                        this_reviewers_grades = admin_provided_grades
                    else:
                        return None
                user_grades[reviewer_id] = this_reviewers_grades
        elif admin_provided_grades:
            group_reviewer_ids = [self.user_id]
            user_grades[self.user_id] = admin_provided_grades
        else:
            return None

        # Okay, if we've got here we have a complete set of marks to calculate the grade
        reviewer_grades = [
            mean(user_grades[reviewer_id])
            for reviewer_id in group_reviewer_ids
            if len(user_grades[reviewer_id]) > 0
        ]
        group_grade = round(mean(reviewer_grades)) if len(reviewer_grades) > 0 else None

        return group_grade

    def mark_complete_stage(self, user_id, stage):
        try:
            self.project_api.mark_as_complete(
                self.course_id,
                self.content_id,
                user_id,
                stage
            )
        except ApiError as e:
            # 409 indicates that the completion record already existed
            # That's ok in this case
            if e.code != 409:
                raise

    def update_upload_complete(self):
        for u in self.workgroup["users"]:
            self.mark_complete_stage(u["id"], "upload")

    def graded_and_complete(self, group_id):
        workgroup = self.project_api.get_workgroup_by_id(group_id)
        for u in workgroup["users"]:
            self.mark_complete_stage(u["id"], None)

    def evaluations_complete(self):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
        peer_review_stages = [stage for stage in group_activity.activity_stages if
                              stage.peer_reviews]
        peer_review_questions = []
        for peer_review_stage in peer_review_stages:
            for peer_review_section in peer_review_stage.peer_review_sections:
                peer_review_questions.extend(
                    [question.id for question in peer_review_section.questions if question.required])

        group_peer_items = self.project_api.get_peer_review_items_for_group(self.workgroup['id'], self.content_id)
        my_feedback = {
            make_key(peer_review_item["user"], peer_review_item["question"]): peer_review_item["answer"]
            for peer_review_item in group_peer_items
            if peer_review_item['reviewer'] == self.xmodule_runtime.anonymous_student_id
        }
        my_peers = [user for user in self.workgroup["users"] if user["id"] != self.user_id]

        for peer in my_peers:
            for question_id in peer_review_questions:
                k = make_key(peer["id"], question_id)
                if k not in my_feedback:
                    return False
                if my_feedback[k] is None:
                    return False
                if my_feedback[k] == '':
                    return False

        return True

    def grading_complete(self):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
        group_review_stages = [stage for stage in group_activity.activity_stages if
                               stage.other_group_reviews]
        group_review_questions = []
        for group_review_stage in group_review_stages:
            for review_section in group_review_stage.other_group_sections:
                group_review_questions.extend([q.id for q in review_section.questions if q.required])

        group_review_items = []
        assess_groups = self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        for assess_group in assess_groups:
            group_review_items.extend(
                self.project_api.get_workgroup_review_items_for_group(assess_group["id"], self.content_id))
        my_feedback = {
            make_key(peer_review_item["workgroup"], peer_review_item["question"]): peer_review_item["answer"]
            for peer_review_item in group_review_items
            if peer_review_item['reviewer'] == self.xmodule_runtime.anonymous_student_id
        }

        for assess_group in assess_groups:
            for question_id in group_review_questions:
                key = make_key(assess_group["id"], question_id)
                if key not in my_feedback:
                    return False
                if my_feedback[key] is None:
                    return False
                if my_feedback[key] == '':
                    return False

        return True

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):

        self.display_name = submissions['display_name']
        xml_content = submissions['data']
        max_score = submissions['max_score']
        group_reviews_required_count = submissions['group_reviews_required_count']
        user_review_count = submissions['user_review_count']

        # TODO: Better use validations than using default values to mask errors
        if not max_score:
            # empty = default
            max_score = 100
        else:
            try:
                # not an integer, then default
                max_score = int(max_score)
            except:
                max_score = 100

        self.weight = max_score

        try:
            group_reviews_required_count = int(group_reviews_required_count)
        except:
            group_reviews_required_count = 3

        self.group_reviews_required_count = group_reviews_required_count

        try:
            user_review_count = int(user_review_count)
        except:
            user_review_count = 1

        self.user_review_count = user_review_count

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
    def submit_peer_feedback(self, submissions, suffix=''):
        try:
            peer_id = submissions["peer_id"]
            del submissions["peer_id"]

            # Then something like this needs to happen
            self.project_api.submit_peer_review_items(
                self.xmodule_runtime.anonymous_student_id,
                peer_id,
                self.workgroup['id'],
                self.content_id,
                submissions,
            )

            if self.evaluations_complete():
                self.mark_complete_stage(self.user_id, "evaluation")

        except Exception as e:
            return {
                'result': 'error',
                'msg': e.message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

    @XBlock.json_handler
    def submit_other_group_feedback(self, submissions, suffix=''):
        try:
            group_id = submissions["group_id"]
            del submissions["group_id"]

            self.project_api.submit_workgroup_review_items(
                self.xmodule_runtime.anonymous_student_id,
                group_id,
                self.content_id,
                submissions
            )

            group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
            for question_id in group_activity.grade_questions:
                if question_id in submissions:
                    # Emit analytics event...
                    self.runtime.publish(
                        self,
                        "group_activity.received_grade_question_score",
                        {
                            "question": question_id,
                            "answer": submissions[question_id],
                            "reviewer_id": self.xmodule_runtime.anonymous_student_id,
                            "is_admin_grader": self.is_admin_grader,
                            "group_id": group_id,
                            "content_id": self.content_id,
                        }
                    )

            grade_value = self.calculate_grade(group_id)
            if grade_value:
                self.assign_grade_to_group(group_id, grade_value)
                self.graded_and_complete(group_id)

            if self.is_group_member and self.grading_complete():
                self.mark_complete_stage(self.user_id, "grade")

        except Exception as e:
            return {
                'result': 'error',
                'msg': e.message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

    @XBlock.handler
    def load_peer_feedback(self, request, suffix=''):

        peer_id = request.GET["peer_id"]
        feedback = self.project_api.get_peer_review_items(
            self.xmodule_runtime.anonymous_student_id,
            peer_id,
            self.workgroup['id'],
            self.content_id,
        )

        # pivot the data to show question -> answer
        results = {pi['question']: pi['answer'] for pi in feedback}

        return webob.response.Response(body=json.dumps(results))

    @XBlock.handler
    def load_other_group_feedback(self, request, suffix=''):

        group_id = request.GET["group_id"]

        feedback = self.project_api.get_workgroup_review_items(
            self.xmodule_runtime.anonymous_student_id,
            group_id,
            self.content_id
        )

        # pivot the data to show question -> answer
        results = {ri['question']: ri['answer'] for ri in feedback}

        return webob.response.Response(body=json.dumps(results))

    @XBlock.handler
    def load_my_peer_feedback(self, request, suffix=''):

        user_id = self.user_id
        feedback = self.project_api.get_user_peer_review_items(
            user_id,
            self.workgroup['id'],
            self.content_id,
        )

        results = {}
        for item in feedback:
            # TODO: results could be defaultdict(list)
            if item['question'] in results:
                results[item['question']].append(html.escape(item['answer']))
            else:
                results[item['question']] = [html.escape(item['answer'])]

        return webob.response.Response(body=json.dumps(results))

    @XBlock.handler
    def load_my_group_feedback(self, request, suffix=''):
        workgroup_id = self.workgroup['id']
        feedback = self.project_api.get_workgroup_review_items_for_group(
            workgroup_id,
            self.content_id,
        )

        results = {}
        for item in feedback:
            # TODO: results could be defaultdict(list)
            if item['question'] in results:
                results[item['question']].append(html.escape(item['answer']))
            else:
                results[item['question']] = [html.escape(item['answer'])]

        final_grade = self.calculate_grade(workgroup_id)
        if final_grade:
            results["final_grade"] = [final_grade]

        return webob.response.Response(body=json.dumps(results))

    @XBlock.handler
    def upload_submission(self, request, suffix=''):
        response_data = {"message": _("File(s) successfully submitted")}
        failure_code = 0
        try:
            group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

            context = {
                "user_id": self.user_id,
                "group_id": self.workgroup['id'],
                "project_api": self.project_api,
                "course_id": self.course_id
            }

            upload_files = [UploadFile(request.params[submission.id].file, submission.id, context)
                            for submission in group_activity.submissions if submission.id in request.params]

            # Save the files first
            for uf in upload_files:
                try:
                    uf.save_file()
                except Exception as save_file_error:
                    original_message = save_file_error.message if hasattr(save_file_error, "message") else ""
                    save_file_error.message = _("Error storing file {} - {}").format(uf.file.name, original_message)
                    raise

            # They all got saved... note the submissions
            at_least_one_success = False
            for uf in upload_files:
                try:
                    uf.submit()
                    # Emit analytics event...
                    self.runtime.publish(
                        self,
                        "group_activity.received_submission",
                        {
                            "submission_id": uf.submission_id,
                            "filename": uf.file.name,
                            "content_id": self.content_id,
                            "group_id": self.workgroup['id'],
                            "user_id": self.user_id,
                        }
                    )
                    at_least_one_success = True
                except Exception as save_record_error:
                    original_message = save_record_error.message if hasattr(save_record_error, "message") else ""
                    save_record_error.message = _("Error recording file information {} - {}").format(uf.file.name,
                                                                                                     original_message)
                    raise

            if at_least_one_success:
                # See if the xBlock Notification Service is available, and - if so -
                # dispatch a notification to the entire workgroup that a file has been uploaded
                # Note that the NotificationService can be disabled, so it might not be available
                # in the list of services
                notifications_service = self.runtime.service(self, 'notifications')
                if notifications_service:
                    self.fire_file_upload_notification(notifications_service)

            response_data.update({uf.submission_id: uf.file_url for uf in upload_files})

            group_activity.update_submission_data(
                self.project_api.get_latest_workgroup_submissions_by_id(self.workgroup['id'])
            )
            if group_activity.has_all_submissions:
                self.update_upload_complete()

        except Exception as e:
            log.exception(e)
            failure_code = 500
            if isinstance(e, ApiError):
                failure_code = e.code
            if not hasattr(e, "message"):
                e.message = _("Error uploading at least one file")
            response_data.update({"message": e.message})

        response = webob.response.Response(body=json.dumps(response_data))
        if failure_code:
            response.status_code = failure_code

        return response

    @XBlock.handler
    def other_submission_links(self, request, suffix=''):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
        group_id = request.GET["group_id"]

        # TODO: this update_submission_data is common as well - might make sense to extract a method
        group_activity.update_submission_data(
            self.project_api.get_latest_workgroup_submissions_by_id(group_id)
        )
        html_output = render_template('/templates/html/review_submissions.html', {"group_activity": group_activity})

        return webob.response.Response(body=json.dumps({"html": html_output}))

    @XBlock.handler
    def refresh_submission_links(self, request, suffix=''):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

        group_activity.update_submission_data(
            self.project_api.get_latest_workgroup_submissions_by_id(self.workgroup['id'])
        )
        html_output = render_template('/templates/html/submission_links.html', {"group_activity": group_activity})

        return webob.response.Response(body=json.dumps({"html": html_output}))

    def get_courseware_info(self, courseware_parent_info_service):
        activity_name = self.display_name
        activity_location = None
        stage_name = self.display_name
        stage_location = None

        try:
            if courseware_parent_info_service:
                # First get Unit (first parent)
                stage_info = courseware_parent_info_service.get_parent_info(
                    self.location
                )
                stage_location = stage_info['location']
                stage_name = stage_info['display_name']

                # Then get Sequence (second parent)
                activity_courseware_info = courseware_parent_info_service.get_parent_info(
                    stage_location
                )
                activity_name = activity_courseware_info['display_name']
                activity_location = activity_courseware_info['location']

                project_courseware_info = courseware_parent_info_service.get_parent_info(
                    activity_location
                )
                project_name = project_courseware_info['display_name']
                project_location = project_courseware_info['location']

        except Exception, ex:
            # Can't look this up then log and just use the default
            # which is our display_name
            log.exception(ex)

        return {
            'stage_name': stage_name,
            'stage_location': stage_location,
            'activity_name': activity_name,
            'activity_location': activity_location,
            'project_name': project_name,
            'project_location': project_location,
        }

    # TODO: this fire_* methods are mostly identical - might make sense to refactor into single method
    def fire_file_upload_notification(self, notifications_service):
        try:
            # this NotificationType is registered in the list of default Open edX Notifications
            msg_type = notifications_service.get_notification_type('open-edx.xblock.group-project.file-uploaded')

            workgroup_user_ids = []
            uploader_username = ''
            for user in self.workgroup['users']:
                # don't send to ourselves
                if user['id'] != self.user_id:
                    workgroup_user_ids.append(user['id'])
                else:
                    uploader_username = user['username']

            # get the activity name which is simply our hosting
            # Sequence's Display Name, so call out to a new xBlock
            # runtime Service

            courseware_info = self.get_courseware_info(self.runtime.service(self, 'courseware_parent_info'))

            activity_name = courseware_info['activity_name']
            activity_location = courseware_info['activity_location']

            msg = NotificationMessage(
                msg_type=msg_type,
                namespace=unicode(self.course_id),
                payload={
                    '_schema_version': 1,
                    'action_username': uploader_username,
                    'activity_name': activity_name,
                }
            )

            #
            # add in all the context parameters we'll need to
            # generate a URL back to the website that will
            # present the new course announcement
            #
            # IMPORTANT: This can be changed to msg.add_click_link() if we
            # have a particular URL that we wish to use. In the initial use case,
            # we need to make the link point to a different front end website
            # so we need to resolve these links at dispatch time
            #
            msg.add_click_link_params({
                'course_id': unicode(self.course_id),
                'activity_location': unicode(activity_location) if activity_location else '',
            })

            # NOTE: We're not using Celery here since we are expectating that we
            # will have only a very small handful of workgroup users
            notifications_service.bulk_publish_notification_to_users(
                workgroup_user_ids,
                msg
            )
        except Exception, ex:
            # While we *should* send notification, if there is some
            # error here, we don't want to blow the whole thing up.
            # So log it and continue....
            log.exception(ex)

    def fire_grades_posted_notification(self, group_id, notifications_service):
        try:
            # this NotificationType is registered in the list of default Open edX Notifications
            msg_type = notifications_service.get_notification_type('open-edx.xblock.group-project.grades-posted')

            # get the activity name which is simply our hosting
            # Sequence's Display Name, so call out to a new xBlock
            # runtime Service
            courseware_info = self.get_courseware_info(self.runtime.service(self, 'courseware_parent_info'))
            activity_name = courseware_info['activity_name']
            activity_location = courseware_info['activity_location']

            msg = NotificationMessage(
                msg_type=msg_type,
                namespace=unicode(self.course_id),
                payload={
                    '_schema_version': 1,
                    'activity_name': activity_name,
                }
            )

            #
            # add in all the context parameters we'll need to
            # generate a URL back to the website that will
            # present the new course announcement
            #
            # IMPORTANT: This can be changed to msg.add_click_link() if we
            # have a particular URL that we wish to use. In the initial use case,
            # we need to make the link point to a different front end website
            # so we need to resolve these links at dispatch time
            #
            msg.add_click_link_params({
                'course_id': unicode(self.course_id),
                'activity_location': unicode(activity_location) if activity_location else '',
            })

            # Bulk publish to the 'group_project_workgroup' user scope
            notifications_service.bulk_publish_notification_to_scope(
                'group_project_workgroup',
                {
                    # I think self.workgroup['id'] is a string version of an integer
                    'workgroup_id': group_id,
                },
                msg
            )
        except Exception, ex:
            # While we *should* send notification, if there is some
            # error here, we don't want to blow the whole thing up.
            # So log it and continue....
            log.exception(ex)

    def _get_stage_timer_name(self, stage, timer_name_suffix):
        return '{location}-{stage}-{timer_name_suffix}'.format(
            location=self.location,
            stage=stage.id,
            timer_name_suffix=timer_name_suffix
        )

    def _set_activity_timed_notification(self, course_id, activity, msg_type, stage, activity_date, send_at_date,
                                         services, timer_name_suffix):

        stage_name = stage.name
        notifications_service = services.get('notifications')
        courseware_parent_info = services.get('courseware_parent_info')

        courseware_info = self.get_courseware_info(courseware_parent_info)

        activity_name = courseware_info['activity_name']
        activity_location = courseware_info['activity_location']

        project_location = courseware_info['project_location']

        activity_date_tz = activity_date.replace(tzinfo=pytz.UTC)
        send_at_date_tz = send_at_date.replace(tzinfo=pytz.UTC)

        msg = NotificationMessage(
            msg_type=notifications_service.get_notification_type(msg_type),
            namespace=unicode(course_id),
            payload={
                '_schema_version': 1,
                'activity_name': activity_name,
                'stage': stage_name,
                'due_date': activity_date_tz.strftime('%-m/%-d/%-y'),
            }
        )

        #
        # add in all the context parameters we'll need to
        # generate a URL back to the website that will
        # present the new course announcement
        #
        # IMPORTANT: This can be changed to msg.add_click_link() if we
        # have a particular URL that we wish to use. In the initial use case,
        # we need to make the link point to a different front end website
        # so we need to resolve these links at dispatch time
        #
        msg.add_click_link_params({
            'course_id': unicode(course_id),
            'activity_location': unicode(activity_location),
        })

        notifications_service.publish_timed_notification(
            msg=msg,
            send_at=send_at_date_tz,
            # send to all students participating in this project
            scope_name='group_project_participants',
            scope_context={
                'course_id': unicode(course_id),
                'content_id': unicode(project_location),
            },
            timer_name=self._get_stage_timer_name(stage, timer_name_suffix),
            ignore_if_past_due=True  # don't send if we're already late!
        )

    def on_studio_published(self, course_id, services):
        """
        A hook into when this xblock is published in Studio. When we are published we should
        register a Notification to be send on key dates
        """
        try:
            log.info('GroupActivityXBlock.on_published() on location = {}'.format(self.location))

            group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # set (or update) Notification timed message based on
                # the current key dates
                for stage in group_activity.activity_stages:

                    # if the stage has a opening date, then send a msg then
                    if stage.open_date:
                        self._set_activity_timed_notification(
                            course_id,
                            group_activity,
                            u'open-edx.xblock.group-project.stage-open',
                            stage,
                            datetime.combine(stage.open_date, datetime.min.time()),
                            datetime.combine(stage.open_date, datetime.min.time()),
                            services,
                            'open'
                        )

                    # if the stage has a close date, then send a msg then
                    if stage.close_date:
                        self._set_activity_timed_notification(
                            course_id,
                            group_activity,
                            u'open-edx.xblock.group-project.stage-due',
                            stage,
                            datetime.combine(stage.close_date, datetime.min.time()),
                            datetime.combine(stage.close_date, datetime.min.time()),
                            services,
                            'due'
                        )

                        # and also send a notice 3 days earlier
                        self._set_activity_timed_notification(
                            course_id,
                            group_activity,
                            u'open-edx.xblock.group-project.stage-due',
                            stage,
                            datetime.combine(stage.close_date, datetime.min.time()),
                            datetime.combine(stage.close_date, datetime.min.time()) - timedelta(days=3),
                            services,
                            'coming-due'
                        )

        except Exception, ex:
            log.exception(ex)

    def on_before_studio_delete(self, course_id, services):
        """
        A hook into when this xblock is deleted in Studio, for xblocks to do any lifecycle
        management
        """
        log.info('GroupActivityXBlock.on_before_delete() on location = {}'.format(self.location))

        try:
            group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # If we are being delete, then we should remove any NotificationTimers that
                # may have been registered before
                for stage in group_activity.activity_stages:
                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'open')
                    )

                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'due')
                    )

                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'coming-due')
                    )

        except Exception, ex:
            log.exception(ex)

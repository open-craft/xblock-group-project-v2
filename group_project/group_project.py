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
        default=100.0
    )

    group_reviews_required_count = Integer(
        display_name="Reviews Required Minimum",
        help="The minimum number of group-reviews that should be applied to a set of submissions (set to 0 to be 'TA Graded')",
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
            self._known_real_user_ids[anonymous_student_id] = self.xmodule_runtime.get_real_user(anonymous_student_id).id
        return self._known_real_user_ids[anonymous_student_id]

    @property
    def milestone_dates(self):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
        return group_activity.milestone_dates

    @property
    def project_api(self):
        if self._project_api is None:
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

    @property
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
            error_fragment.add_content(render_template('/templates/html/loading_error.html', {'error_message': unicode(ode)}))
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
                team_members = [self.project_api.get_user_details(tm["id"]) for tm in workgroup["users"] if user_id != int(tm["id"])]
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
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/vendor/jquery.iframe-transport.js'))

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


    def calculate_grade(self, group_id):

        def mean(value_array):
            numeric_values = [float(v) for v in value_array]
            return float(sum(numeric_values)/len(numeric_values))

        review_item_data = self.project_api.get_workgroup_review_items_for_group(group_id, self.content_id)
        review_item_map = {make_key(r['question'], self.real_user_id(r['reviewer'])) : r['answer'] for r in review_item_data}
        all_reviewer_ids = set([self.real_user_id(r['reviewer']) for r in review_item_data])
        group_reviewer_ids = [u["id"] for u in self.project_api.get_workgroup_reviewers(group_id)]
        admin_reviewer_ids = [ar_id for ar_id in all_reviewer_ids if ar_id not in group_reviewer_ids]

        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

        def get_user_grade_value_list(user_id):
            user_grades = []
            for q_id in group_activity.grade_questions:
                user_value = review_item_map.get(make_key(q_id, user_id), None)
                if user_value is None:
                    # if any are incomplete, we consider the whole set to be unusable
                    return None
                else:
                    user_grades.append(user_value)

            return user_grades

        admin_provided_grades = None
        if len(admin_reviewer_ids) > 0:
            admin_provided_grades = []
            admin_reviewer_grades = [get_user_grade_value_list(admin_id) for admin_id in admin_reviewer_ids]
            admin_grader_count = len(admin_reviewer_grades)
            if admin_grader_count > 1:
                for idx in range(admin_grader_count):
                    admin_provided_grades.append(mean([adm[idx] for adm in admin_reviewer_grades]))
            else:
                admin_provided_grades = admin_reviewer_grades[0]

        user_grades = {}
        if len(group_reviewer_ids) > 0:
            for r_id in group_reviewer_ids:
                this_reviewers_grades = get_user_grade_value_list(r_id)
                if this_reviewers_grades is None:
                    if admin_provided_grades:
                        this_reviewers_grades = admin_provided_grades
                    else:
                        return None
                user_grades[r_id] = this_reviewers_grades
        elif admin_provided_grades:
            group_reviewer_ids = [self.user_id]
            user_grades[self.user_id] = admin_provided_grades
        else:
            return None

        # Okay, if we've got here we have a complete set of marks to calculate the grade
        reviewer_grades = [mean(user_grades[r_id]) for r_id in group_reviewer_ids if len(user_grades[r_id]) > 0]
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
        peer_review_components = [c for c in group_activity.activity_components if c.peer_reviews]
        peer_review_questions = []
        for prc in peer_review_components:
            for sec in prc.peer_review_sections:
                peer_review_questions.extend([q.id for q in sec.questions if q.required])

        group_peer_items = self.project_api.get_peer_review_items_for_group(self.workgroup['id'], self.content_id)
        my_feedback = {make_key(pri["user"], pri["question"]): pri["answer"] for pri in group_peer_items if pri['reviewer'] == self.xmodule_runtime.anonymous_student_id}
        my_peers = [u for u in self.workgroup["users"] if u["id"] != self.user_id]

        for peer in my_peers:
            for q_id in peer_review_questions:
                k = make_key(peer["id"], q_id)
                if not k in my_feedback:
                    return False
                if my_feedback[k] is None:
                    return False
                if my_feedback[k] == '':
                    return False

        return True

    def grading_complete(self):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)
        group_review_components = [c for c in group_activity.activity_components if c.other_group_reviews]
        group_review_questions = []
        for prc in group_review_components:
            for sec in prc.other_group_sections:
                group_review_questions.extend([q.id for q in sec.questions if q.required])

        group_review_items = []
        assess_groups = self.project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        for assess_group in assess_groups:
            group_review_items.extend(self.project_api.get_workgroup_review_items_for_group(assess_group["id"], self.content_id))
        my_feedback = {make_key(pri["workgroup"], pri["question"]): pri["answer"] for pri in group_review_items if pri['reviewer'] == self.xmodule_runtime.anonymous_student_id}

        for assess_group in assess_groups:
            for q_id in group_review_questions:
                k = make_key(assess_group["id"], q_id)
                if not k in my_feedback:
                    return False
                if my_feedback[k] is None:
                    return False
                if my_feedback[k] == '':
                    return False

        return True

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):

        self.display_name = submissions['display_name']
        xml_content = submissions['data']
        max_score = submissions['max_score']
        group_reviews_required_count = submissions['group_reviews_required_count']
        user_review_count = submissions['user_review_count']

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
            for q_id in group_activity.grade_questions:
                if q_id in submissions:
                    # Emit analytics event...
                    self.runtime.publish(
                        self,
                        "group_activity.received_grade_question_score",
                        {
                            "question": q_id,
                            "answer": submissions[q_id],
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

            upload_files = [UploadFile(request.params[s.id].file, s.id, context)
                            for s in group_activity.submissions if s.id in request.params]

            # Save the files first
            for uf in upload_files:
                try:
                    uf.save_file()
                except Exception as save_file_error:
                    original_message = save_file_error.message if hasattr(save_file_error, "message") else ""
                    save_file_error.message = _("Error storing file {} - {}").format(uf.file.name, original_message)
                    raise

            # They all got saved... note the submissions
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
                except Exception as save_record_error:
                    original_message = save_record_error.message if hasattr(save_record_error, "message") else ""
                    save_record_error.message = _("Error recording file information {} - {}").format(uf.file.name, original_message)
                    raise

            response_data.update({uf.submission_id : uf.file_url for uf in upload_files})

            group_activity.update_submission_data(
                self.project_api.get_latest_workgroup_submissions_by_id(self.workgroup['id'])
            )
            if group_activity.has_all_submissions:
                self.update_upload_complete()

        except Exception as e:
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

        group_activity.update_submission_data(
            self.project_api.get_latest_workgroup_submissions_by_id(group_id)
        )
        html_output = render_template('/templates/html/submission_links.html', {"group_activity": group_activity})

        return webob.response.Response(body=json.dumps({"html":html_output}))

    @XBlock.handler
    def refresh_submission_links(self, request, suffix=''):
        group_activity = GroupActivity.import_xml_string(self.data, self.is_admin_grader)

        group_activity.update_submission_data(
            self.project_api.get_latest_workgroup_submissions_by_id(self.workgroup['id'])
        )
        html_output = render_template('/templates/html/submission_links.html', {"group_activity": group_activity})

        return webob.response.Response(body=json.dumps({"html":html_output}))

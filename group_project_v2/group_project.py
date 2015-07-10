# -*- coding: utf-8 -*-
#
# TODO: lots of broad except clauses - disabled in pylint, but might make sense to clean them up
# Imports ###########################################################

import logging
import json
import itertools
from lazy.lazy import lazy
import pytz
import webob
from datetime import datetime, timedelta

from django.utils import html
from django.utils.translation import ugettext as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Float, Integer
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.studio_editable import StudioEditableXBlockMixin, StudioContainerXBlockMixin

from group_project_v2.mixins import ChildrenNavigationXBlockMixin, UserAwareXBlockMixin, CourseAwareXBlockMixin, \
    WorkgroupAwareXBlockMixin
from group_project_v2.utils import loader, OutsiderDisallowedError
from group_project_v2.stage import (
    BasicStage, SubmissionStage, PeerReviewStage, GroupReviewStage,
    PeerAssessmentStage, GroupAssessmentStage
)
from group_project_v2.project_api import project_api
from group_project_v2.api_error import ApiError

try:
    from edx_notifications.data import NotificationMessage  # pylint: disable=import-error
except ImportError:
    # Notifications is an optional runtime configuration, so it may not be available for import
    pass


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


def make_key(*args):
    return ":".join([str(a) for a in args])


class GroupProjectXBlock(XBlock, StudioEditableXBlockMixin, StudioContainerXBlockMixin):
    display_name = String(
        display_name="Display Name",
        help="This is a name of the project",
        scope=Scope.settings,
        default="Group Project V2"
    )

    editable_fields = ('display_name', )
    has_score = False
    has_children = True

    def student_view(self, context):
        fragment = Fragment()
        for child_id in self.children:
            child = self.runtime.get_block(child_id)
            rendered_child_fragment = child.render('student_view', context)
            fragment.add_frag_resources(rendered_child_fragment)
            fragment.add_content(rendered_child_fragment.content)
        return fragment

    def author_preview_view(self, context):
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/group_project_preview.css"))
        return fragment

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(loader.render_template('templates/html/group_project_add_buttons.html', {}))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        return fragment

    @lazy
    def activities(self):
        all_children = [self.runtime.get_block(child_id) for child_id in self.children]
        return [child for child in all_children if isinstance(child, GroupActivityXBlock)]


class ActivityNavigationViewMixin(object):
    def navigation_view(self, context):
        fragment = Fragment()

        stage_contents = []
        for child in self.stages:
            child_fragment = child.render('navigation_view', context)
            fragment.add_frag_resources(child_fragment)
            stage_contents.append(child_fragment.content)

        context = {'activity': self, 'stage_contents': stage_contents}
        fragment.add_content(loader.render_template("templates/html/activity/navigation_view.html", context))

        return fragment


class ActivityResourcesViewMixin(object):
    def resources_view(self, context):
        fragment = Fragment()

        has_resources = any([bool(stage.resources) for stage in self.stages])

        stage_contents = []
        for child in self.stages:
            child_fragment = child.render('resources_view', context)
            fragment.add_frag_resources(child_fragment)
            stage_contents.append(child_fragment.content)

        context = {'activity': self, 'stage_contents': stage_contents, 'has_resources': has_resources}
        fragment.add_content(loader.render_template("templates/html/activity/resources_view.html", context))

        return fragment


class ActivitySubmissionsViewMixin(object):
    def submissions_view(self, context):
        fragment = Fragment()

        target_stages = [stage for stage in self.stages if isinstance(stage, SubmissionStage)]

        has_submissions = any([stage.has_submissions for stage in target_stages])

        stage_contents = []
        for child in target_stages:
            child_fragment = child.render('submissions_view', context)
            fragment.add_frag_resources(child_fragment)
            stage_contents.append(child_fragment.content)

        context = {'activity': self, 'stage_contents': stage_contents, 'has_submissions': has_submissions}
        fragment.add_content(loader.render_template("templates/html/activity/submissions_view.html", context))

        return fragment



# TODO: enable and fix these violations
# pylint: disable=unused-argument,invalid-name
@XBlock.wants('notifications')
@XBlock.wants('courseware_parent_info')
class GroupActivityXBlock(
    XBlock, ChildrenNavigationXBlockMixin,StudioEditableXBlockMixin, StudioContainerXBlockMixin,
    CourseAwareXBlockMixin, UserAwareXBlockMixin, WorkgroupAwareXBlockMixin,
    ActivityNavigationViewMixin, ActivityResourcesViewMixin, ActivitySubmissionsViewMixin
):
    """
    XBlock providing a group activity project for a group of students to collaborate upon
    """
    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Group Project Activity"
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

    editable_fields = ("display_name", "weight", "group_reviews_required_count", "user_review_count")
    has_score = True
    has_children = True

    @property
    def id(self):
        return self.scope_ids.usage_id

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
        except Exception:  # pylint: disable=broad-except
            return self.id

    @property
    def allowed_nested_blocks(self):
        return {
            BasicStage.CATEGORY: _(u"Text Stage"),
            SubmissionStage.CATEGORY: _(u"Submission Stage"),
            PeerReviewStage.CATEGORY: _(u"Peer Review Stage"),
            GroupReviewStage.CATEGORY: _(u"Group Review Stage"),
            PeerAssessmentStage.CATEGORY: _(u"Peer Assessment Stage"),
            GroupAssessmentStage.CATEGORY: _(u"Group Assessment Stage"),
        }

    @property
    def stages(self):
        return self._children

    def _get_initialization_data(self):
        return {
            "default_stage_id": unicode(self._get_default_stage_id())
        }

    def _get_default_stage_id(self):
        default_stage_id = self.stages[0].id
        for stage in self.stages:
            # TODO: this will likely need some other way to select target stage, or could be removed altogether
            if self.is_admin_grader:
                if isinstance(stage, GroupReviewStage):
                    default_stage_id = stage.id
            elif stage.is_open:
                default_stage_id = stage.id

        return default_stage_id

    @property
    def team_members(self):
        """
        Returns teammates to review. May throw `class`: OutsiderDisallowedError
        """
        if not self.is_group_member:
            return []

        try:
            return [
                project_api.get_user_details(team_member["id"])
                for team_member in self.workgroup["users"]
                if self.user_id != int(team_member["id"])
            ]
        except ApiError:
            return []

    @property
    def review_groups(self):
        """
        Returns groups to review. May throw `class`: OutsiderDisallowedError
        """
        if not self.is_group_member:
            return self.workgroup

        try:
            return project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)
        except ApiError:
            return []

    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        try:
            team_members = self.team_members
            review_groups = self.review_groups
        except OutsiderDisallowedError as ode:
            error_fragment = Fragment()
            error_fragment.add_content(
                loader.render_template('/templates/html/loading_error.html', {'error_message': unicode(ode)}))
            error_fragment.add_javascript(loader.load_unicode('public/js/group_project_error.js'))
            error_fragment.initialize_js('GroupProjectError')
            return error_fragment

        fragment = Fragment()
        stage_contents = []
        for stage in self.stages:
            stage_fragment = stage.render('student_view', context)
            fragment.add_frag_resources(stage_fragment)
            stage_contents.append(stage_fragment.content)

        context = {
            "stage_contents": stage_contents,
            "initialization_data": json.dumps(self._get_initialization_data()),
            "team_members": json.dumps(team_members),
            "assess_groups": json.dumps(review_groups),
        }

        fragment.add_content(loader.render_template('/templates/html/activity/student_view.html', context))
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_activity.css'))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/group_activity.js'))

        fragment.initialize_js('GroupProjectBlock')

        return fragment

    def author_preview_view(self, context):
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        return fragment

    def author_edit_view(self, context):
        """
        Add some HTML to the author view that allows authors to add child blocks.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=True, can_add=False)
        fragment.add_content(
            loader.render_template('templates/html/add_buttons.html', {'child_blocks': self.allowed_nested_blocks})
        )
        fragment.add_css_url(self.runtime.local_resource_url(self, 'public/css/group_project_edit.css'))
        return fragment

    def assign_grade_to_group(self, group_id, grade_value):
        project_api.set_group_grade(
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

    @property
    def grade_questions(self):
        return list(itertools.chain(
            *[getattr(stage, 'grade_questions', ()) for stage in self.activity_stages]
        ))

    def calculate_grade(self, group_id):

        def mean(value_array):
            numeric_values = [float(v) for v in value_array]
            return float(sum(numeric_values) / len(numeric_values))

        review_item_data = project_api.get_workgroup_review_items_for_group(group_id, self.content_id)
        review_item_map = {
            make_key(review_item['question'], self.real_user_id(review_item['reviewer'])): review_item['answer']
            for review_item in review_item_data
        }
        all_reviewer_ids = set([self.real_user_id(review_item['reviewer']) for review_item in review_item_data])
        group_reviewer_ids = [user["id"] for user in project_api.get_workgroup_reviewers(group_id)]
        admin_reviewer_ids = [reviewer_id for reviewer_id in all_reviewer_ids if reviewer_id not in group_reviewer_ids]

        def get_user_grade_value_list(user_id):
            user_grades = []
            for question in self.grade_questions:
                user_value = review_item_map.get(make_key(question.id, user_id), None)
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
                for idx in range(len(self.grade_questions)):
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

    def mark_complete_stage(self, user_id, stage_id):
        try:
            project_api.mark_as_complete(self.course_id, self.content_id, user_id, stage_id)
        except ApiError as e:
            # 409 indicates that the completion record already existed. That's ok in this case
            if e.code != 409:
                raise

    def graded_and_complete(self, group_id):
        workgroup = project_api.get_workgroup_by_id(group_id)
        for u in workgroup["users"]:
            self.mark_complete_stage(u["id"], None)

    def _get_review_questions(self, stage_id):
        stage = [stage for stage in self.stages if stage.id == stage_id][0]
        return [question for question in stage.questions if question.required]

    def _check_review_complete(self, items_to_grade, review_questions, review_items, review_item_key):
        my_feedback = {
            make_key(peer_review_item[review_item_key], peer_review_item["question"]): peer_review_item["answer"]
            for peer_review_item in review_items
            if peer_review_item['reviewer'] == self.anonymous_student_id
        }

        for item in items_to_grade:
            for question in review_questions:
                key = make_key(item["id"], question.id)
                if my_feedback.get(key, None) in (None, ''):
                    return False

        return True

    def peer_review_complete(self, stage_id):
        peer_review_questions = self._get_review_questions(stage_id)
        peers_to_review = [user for user in self.workgroup["users"] if user["id"] != self.user_id]
        peer_review_items = project_api.get_peer_review_items_for_group(self.workgroup['id'], self.content_id)

        return self._check_review_complete(peers_to_review, peer_review_questions, peer_review_items, "user")

    def group_review_complete(self, stage_id):
        group_review_questions = self._get_review_questions(stage_id)
        groups_to_review = project_api.get_workgroups_to_review(self.user_id, self.course_id, self.content_id)

        group_review_items = []
        for assess_group in groups_to_review:
            group_review_items.extend(
                project_api.get_workgroup_review_items_for_group(assess_group["id"], self.content_id)
            )

        return self._check_review_complete(groups_to_review, group_review_questions, group_review_items, "workgroup")

    def validate_field_data(self, validation, data):
        super(GroupActivityXBlock, self).validate_field_data(validation, data)
        should_be_ints = ('weight', 'group_reviews_required_count', 'user_review_count')
        for field_name in should_be_ints:
            try:
                int(getattr(data, field_name))
            except (TypeError, ValueError):
                message = _(u"{field_name} must be integer, {field_value} given").format(
                    field_name=field_name, field_value=getattr(data, field_name)
                )
                validation.add(ValidationMessage(ValidationMessage.ERROR, message))

    @XBlock.json_handler
    def submit_peer_feedback(self, submissions, suffix=''):
        try:
            peer_id = submissions["peer_id"]
            stage_id = submissions['stage_id']
            del submissions["peer_id"]
            del submissions['stage_id']

            # Then something like this needs to happen
            project_api.submit_peer_review_items(
                self.anonymous_student_id,
                peer_id,
                self.workgroup['id'],
                self.content_id,
                submissions,
            )

            if self.peer_review_complete(stage_id):
                self.mark_complete_stage(self.user_id, stage_id)

        except ApiError as exception:
            message = exception.message
            log.exception(message)
            return {
                'result': 'error',
                'msg': message,
            }
        except KeyError as exception:
            message = "Missing required argument {}".format(exception.message)
            log.exception(message)
            return {
                'result': 'error',
                'msg': message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

    @XBlock.json_handler
    def submit_other_group_feedback(self, submissions, suffix=''):
        try:
            group_id = submissions["group_id"]
            stage_id = submissions["stage_id"]
            del submissions["group_id"]
            del submissions["stage_id"]

            project_api.submit_workgroup_review_items(
                self.anonymous_student_id,
                group_id,
                self.content_id,
                submissions
            )

            for question_id in self.grade_questions:
                if question_id in submissions:
                    # Emit analytics event...
                    self.runtime.publish(
                        self,
                        "group_activity.received_grade_question_score",
                        {
                            "question": question_id,
                            "answer": submissions[question_id],
                            "reviewer_id": self.anonymous_student_id,
                            "is_admin_grader": self.is_admin_grader,
                            "group_id": group_id,
                            "content_id": self.content_id,
                        }
                    )

            grade_value = self.calculate_grade(group_id)
            if grade_value:
                self.assign_grade_to_group(group_id, grade_value)
                self.graded_and_complete(group_id)

            if self.is_group_member and self.group_review_complete(stage_id):
                self.mark_complete_stage(self.user_id, stage_id)

        except ApiError as exception:
            message = exception.message
            log.exception(message)
            return {
                'result': 'error',
                'msg': message,
            }
        except KeyError as exception:
            message = "Missing required argument {}".format(exception.message)
            log.exception(message)
            return {
                'result': 'error',
                'msg': message,
            }

        return {
            'result': 'success',
            'msg': _('Thanks for your feedback'),
        }

    @XBlock.handler
    def load_other_group_feedback(self, request, suffix=''):

        group_id = request.GET["group_id"]

        feedback = project_api.get_workgroup_review_items(
            self.anonymous_student_id,
            group_id,
            self.content_id
        )

        # pivot the data to show question -> answer
        results = {ri['question']: ri['answer'] for ri in feedback}

        return webob.response.Response(body=json.dumps(results))

    @XBlock.handler
    def load_my_peer_feedback(self, request, suffix=''):

        user_id = self.user_id
        feedback = project_api.get_user_peer_review_items(
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
        feedback = project_api.get_workgroup_review_items_for_group(
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

    def get_courseware_info(self, courseware_parent_info_service):
        activity_name = self.display_name
        activity_location = None
        stage_name = self.display_name
        stage_location = None
        project_name = None
        project_location = None

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

        except Exception, ex:  # pylint: disable=broad-except
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
        except Exception, ex:  # pylint: disable=broad-except
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
        except Exception, ex:  # pylint: disable=broad-except
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

    def _set_activity_timed_notification(self, course_id, msg_type, stage, activity_date, send_at_date,
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

            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # set (or update) Notification timed message based on
                # the current key dates
                for stage in self.stages:

                    # if the stage has a opening date, then send a msg then
                    if stage.open_date:
                        self._set_activity_timed_notification(
                            course_id,
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
                            u'open-edx.xblock.group-project.stage-due',
                            stage,
                            datetime.combine(stage.close_date, datetime.min.time()),
                            datetime.combine(stage.close_date, datetime.min.time()) - timedelta(days=3),
                            services,
                            'coming-due'
                        )

        except Exception, ex:  # pylint: disable=broad-except
            log.exception(ex)

    def on_before_studio_delete(self, course_id, services):  # pylint: disable=unused-argument
        """
        A hook into when this xblock is deleted in Studio, for xblocks to do any lifecycle
        management
        """
        log.info('GroupActivityXBlock.on_before_delete() on location = {}'.format(self.location))

        try:
            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # If we are being delete, then we should remove any NotificationTimers that
                # may have been registered before
                for stage in self.stages:
                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'open')
                    )

                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'due')
                    )

                    notifications_service.cancel_timed_notification(
                        self._get_stage_timer_name(stage, 'coming-due')
                    )

        except Exception, ex:  # pylint: disable=broad-except
            log.exception(ex)

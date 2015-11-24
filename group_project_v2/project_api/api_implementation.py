import json
from urllib import urlencode

from group_project_v2.api_error import api_error_protect
from group_project_v2.json_requests import DELETE, GET, PUT, POST
from group_project_v2.utils import memoize_with_expiration, DEFAULT_EXPIRATION_TIME, build_date_field
from group_project_v2.project_api.dtos import UserDetails, ProjectDetails

API_PREFIX = '/'.join(['api', 'server'])
WORKGROUP_API = '/'.join([API_PREFIX, 'workgroups'])
PEER_REVIEW_API = '/'.join([API_PREFIX, 'peer_reviews'])
WORKGROUP_REVIEW_API = '/'.join([API_PREFIX, 'workgroup_reviews'])
USERS_API = '/'.join([API_PREFIX, 'users'])
SUBMISSION_API = '/'.join([API_PREFIX, 'submissions'])
GROUP_API = '/'.join([API_PREFIX, 'groups'])
COURSES_API = '/'.join([API_PREFIX, 'courses'])


# TODO: this class crosses service boundary, but some methods post-process responses, while other do not
# There're two things to improve:
# * SRP - it should only cross the service boundary, and not do any post-processing
# * Service isolation - it should be used only through some other (not existent yet) class that would ALWAYS do
# post-processing in order to isolate clients from response format changes. As of now, if format changes
# virtually every method in group_project might be affected.
class ProjectAPI(object):
    """
    Deprecated - do not extend or modify. Add new methods and move existing ones to TypedProjectAPI.
    """
    def __init__(self, address, dry_run=False):
        self._api_server_address = address
        self.dry_run = dry_run

    def send_request(self, method, url_parts, data=None, query_params=None, no_trailing_slash=False):
        if self.dry_run:
            return {}

        url_template = "{}/" + "{}/" * len(url_parts)
        url_parameters = [self._api_server_address]
        url_parameters.extend(url_parts)
        url = url_template.format(*url_parameters)  # pylint: disable=star-args
        if no_trailing_slash:
            url = url[:-1]

        if query_params:
            url += "?"+urlencode(query_params)

        if data is not None:
            response = method(url, data)
        else:
            response = method(url)

        if method == DELETE:
            return None

        return json.loads(response.read())

    @api_error_protect
    def get_user_organizations(self, user_id):
        qs_params = {'page_size': 0}
        return self.send_request(GET, (USERS_API, user_id, 'organizations'), query_params=qs_params)

    @api_error_protect
    def get_user_preferences(self, user_id):
        """ gets users preferences information """
        return self.send_request(GET, (USERS_API, user_id, 'preferences'), no_trailing_slash=True)

    @api_error_protect
    def get_peer_review_items_for_group(self, group_id, content_id):
        qs_params = {"content_id": content_id}
        return self.send_request(GET, (WORKGROUP_API, group_id, 'peer_reviews'), query_params=qs_params)

    @api_error_protect
    def update_peer_review_assessment(self, question_data):
        return self.send_request(PUT, (PEER_REVIEW_API, question_data['id']), data=question_data)

    @api_error_protect
    def create_peer_review_assessment(self, question_data):
        return self.send_request(POST, (PEER_REVIEW_API,), data=question_data)

    @api_error_protect
    def delete_peer_review_assessment(self, assessment_id):
        self.send_request(DELETE, (PEER_REVIEW_API, assessment_id))

    @api_error_protect
    # Do not cache - used both in submitting review and calculating grade, so if this call is cached grade calculation
    # sees old value. So, when last review is performed, grade calculation does not see it and returns "No grade yet".
    # See MCKIN-3501 and MCKIN-3471 for what would happen than.
    def get_workgroup_review_items_for_group(self, group_id, content_id):
        qs_params = {"content_id": content_id}
        return self.send_request(GET, (WORKGROUP_API, group_id, 'workgroup_reviews'), query_params=qs_params)

    @api_error_protect
    def create_workgroup_review_assessment(self, question_data):
        return self.send_request(POST, (WORKGROUP_REVIEW_API, ), data=question_data)

    @api_error_protect
    def update_workgroup_review_assessment(self, question_data):
        return self.send_request(PUT, (WORKGROUP_REVIEW_API, question_data['id']), data=question_data)

    @api_error_protect
    def delete_workgroup_review_assessment(self, assessment_id):
        self.send_request(DELETE, (WORKGROUP_REVIEW_API, assessment_id))

    @api_error_protect
    def get_workgroup_by_id(self, group_id):
        return self.send_request(GET, (WORKGROUP_API, group_id))

    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_user_workgroup_for_course(self, user_id, course_id):
        qs_params = {"course_id": course_id}
        workgroups_list = self.send_request(GET, (USERS_API, user_id, 'workgroups'), query_params=qs_params)

        if not workgroups_list or workgroups_list['count'] < 1:
            return None

        return self.get_workgroup_by_id(workgroups_list['results'][0]['id'])

    @api_error_protect
    def get_user_grades(self, user_id, course_id):
        return self.send_request(GET, (USERS_API, user_id, 'courses', course_id, 'grades'), no_trailing_slash=True)

    @api_error_protect
    def set_group_grade(self, group_id, course_id, activity_id, grade_value, max_grade):
        grade_data = {
            "course_id": unicode(course_id),
            "content_id": activity_id,
            "grade": grade_value,
            "max_grade": max_grade,
        }

        return self.send_request(POST, (WORKGROUP_API, group_id, 'grades'), data=grade_data)

    @api_error_protect
    def create_submission(self, submit_hash):
        return self.send_request(POST, (SUBMISSION_API, ), data=submit_hash)

    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_workgroup_submissions(self, group_id):
        return self.send_request(GET, (WORKGROUP_API, group_id, 'submissions'))

    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_review_assignment_groups(self, user_id, course_id, xblock_id):
        qs_params = {
            "course": course_id,
            "type": "reviewassignment",
            "data__xblock_id": xblock_id,
        }
        response = self.send_request(GET, (USERS_API, user_id, 'groups'), query_params=qs_params)
        return response.get("groups", {})

    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_workgroups_for_assignment(self, assignment_id):
        workgroups = self.send_request(GET, (GROUP_API, assignment_id, 'workgroups'), no_trailing_slash=True)
        return workgroups["results"]

    @api_error_protect
    def get_group_detail(self, group_id):
        return self.send_request(GET, (GROUP_API, group_id))

    @api_error_protect
    def get_user_roles_for_course(self, user_id, course_id):
        qs_params = {
            "user_id": user_id,
        }

        return self.send_request(GET, (COURSES_API, course_id, 'roles'), query_params=qs_params)

    # TODO: methods below post-process api response - they should be moved outside of this class.
    # When doing the move, add tests before moving, since there are no test coverage for them
    @api_error_protect
    def get_workgroups_to_review(self, user_id, course_id, xblock_id):
        assignments = self.get_review_assignment_groups(user_id, course_id, xblock_id)

        workgroup_assignments = []
        for assignment in assignments:
            workgroup_assignments += self.get_workgroups_for_assignment(assignment["id"])

        return workgroup_assignments

    @api_error_protect
    def get_workgroup_reviewers(self, group_id, content_id):
        review_assignments = self.send_request(GET, (WORKGROUP_API, group_id, 'groups'), no_trailing_slash=True)

        reviewers = []
        for review_assignment in review_assignments:
            if review_assignment["data"]["xblock_id"] != content_id:
                continue
            # stripping slashes as we're adding it in send_request anyway
            review_assignment_url = review_assignment["url"].strip("/")
            review_assignment_details = self.send_request(GET, (review_assignment_url, 'users'))
            reviewers.extend(review_assignment_details["users"])

        return reviewers

    def get_peer_review_items(self, reviewer_id, peer_id, group_id, content_id):
        teammate_evaluation_items = self.get_peer_review_items_for_group(group_id, content_id)
        return [
            pri for pri in teammate_evaluation_items
            if pri['reviewer'] == reviewer_id and (pri['user'] == peer_id or pri['user'] == int(peer_id))
        ]

    def get_user_peer_review_items(self, user_id, group_id, content_id):
        teammate_evaluation_items = self.get_peer_review_items_for_group(group_id, content_id)
        return [
            pri for pri in teammate_evaluation_items
            if pri['user'] == user_id or pri['user'] == int(user_id)
        ]

    def get_workgroup_review_items(self, reviewer_id, group_id, content_id):
        peer_review_items = self.get_workgroup_review_items_for_group(group_id, content_id)
        return [
            gri for gri in peer_review_items
            if gri['reviewer'] == reviewer_id and gri['content_id'] == content_id
        ]

    def submit_peer_review_items(self, reviewer_id, peer_id, group_id, content_id, data):
        # get any data already there
        current_data = {pi['question']: pi for pi in
                        self.get_peer_review_items(reviewer_id, peer_id, group_id, content_id)}
        for question_id, answer in data.iteritems():
            if question_id in current_data:
                question_data = current_data[question_id]

                if question_data['answer'] != answer:
                    if len(answer) > 0:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = answer

                        self.update_peer_review_assessment(question_data)
                    else:
                        self.delete_peer_review_assessment(question_data['id'])

            elif len(answer) > 0:
                question_data = {
                    "question": question_id,
                    "answer": answer,
                    "workgroup": group_id,
                    "user": peer_id,
                    "reviewer": reviewer_id,
                    "content_id": content_id,
                }
                self.create_peer_review_assessment(question_data)

    def submit_workgroup_review_items(self, reviewer_id, group_id, content_id, data):
        # get any data already there
        current_data = {ri['question']: ri for ri in self.get_workgroup_review_items(reviewer_id, group_id, content_id)}
        for question_id, answer in data.iteritems():
            if question_id in current_data:
                question_data = current_data[question_id]

                if question_data['answer'] != answer:
                    if len(answer) > 0:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = answer

                        self.update_workgroup_review_assessment(question_data)
                    else:
                        self.delete_workgroup_review_assessment(question_data['id'])

            elif len(answer) > 0:
                question_data = {
                    "question": question_id,
                    "answer": answer,
                    "workgroup": group_id,
                    "reviewer": reviewer_id,
                    "content_id": content_id,
                }
                self.create_workgroup_review_assessment(question_data)

    def get_latest_workgroup_submissions_by_id(self, group_id):
        submission_list = self.get_workgroup_submissions(group_id)

        submissions_by_id = {}
        for submission in submission_list:
            submission_id = submission['document_id']
            if submission['user']:
                submission[u'user_details'] = self.get_user_details(submission['user'])
            if submission_id in submissions_by_id:
                last_modified = build_date_field(submissions_by_id[submission_id]["modified"])
                this_modified = build_date_field(submission["modified"])
                if this_modified > last_modified:
                    submissions_by_id[submission["document_id"]] = submission
            else:
                submissions_by_id[submission["document_id"]] = submission

        return submissions_by_id

    def get_member_data(self, user_id):
        user_details = self.get_user_details(user_id)
        user_organizations = self.get_user_organizations(user_id)
        if user_organizations:
            user_details.organization = user_organizations[0]['display_name']
        return user_details


class TypedProjectAPI(ProjectAPI):
    """
    This class is intended to contain methods that return typed responses.
    """
    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_user_details(self, user_id):
        response = self.send_request(GET, (USERS_API, user_id), no_trailing_slash=True)
        return UserDetails(**response)  # pylint: disable=star-args

    @api_error_protect
    @memoize_with_expiration(expires_after=DEFAULT_EXPIRATION_TIME)
    def get_project_details(self, project_id):
        response = self.send_request(GET, (USERS_API, project_id), no_trailing_slash=True)
        return ProjectDetails(**response)  # pylint: disable=star-args



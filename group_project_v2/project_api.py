''' API calls with respect group projects'''
import json
from urllib import urlencode
from django.conf import settings

from group_project_v2.utils import build_date_field
from .json_requests import GET, POST, PUT, DELETE
from .api_error import api_error_protect


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
# pylint: disable=invalid-name
class ProjectAPI(object):
    _api_server_address = None

    def __init__(self, address):
        self._api_server_address = address

    # TODO: self._api_server_address is used virtually everywhere - maybe should extract method, e.g.
    # send_request(GET, USERS_API, user_id, 'preferences')
    # send_request(GET, WORKGROUP_API, group_id, 'preferences', querystring=urlencode(qs_params))
    # send_request(PUT, PEER_REVIEW_API, question_data['id'], data=question_data)

    @api_error_protect
    def get_user_preferences(self, user_id):
        """ gets users preferences information """
        response = GET(
            '{}/{}/{}/preferences'.format(
                self._api_server_address,
                USERS_API,
                user_id,
            ),
        )

        return json.loads(response.read())

    @api_error_protect
    def get_peer_review_items_for_group(self, group_id, content_id):
        qs_params = {
            "content_id": content_id,
        }
        response = GET(
            '{}/{}/{}/peer_reviews/?{}'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id,
                urlencode(qs_params),
            )
        )
        return json.loads(response.read())

    @api_error_protect
    def update_peer_review_assessment(self, question_data):
        response = PUT(
            '{}/{}/{}/'.format(
                self._api_server_address,
                PEER_REVIEW_API,
                question_data['id']
            ),
            question_data
        )
        return json.loads(response.read())

    @api_error_protect
    def create_peer_review_assessment(self, question_data):
        response = POST(
            '{}/{}/'.format(
                self._api_server_address,
                PEER_REVIEW_API
            ),
            question_data
        )
        return json.loads(response.read())

    @api_error_protect
    def delete_peer_review_assessment(self, assessment_id):
        DELETE(
            '{}/{}/{}/'.format(
                self._api_server_address,
                PEER_REVIEW_API,
                assessment_id
            )
        )

    @api_error_protect
    def get_workgroup_review_items_for_group(self, group_id, content_id):
        qs_params = {
            "content_id": content_id,
        }
        response = GET(
            '{}/{}/{}/workgroup_reviews/?{}'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id,
                urlencode(qs_params),
            )
        )
        return json.loads(response.read())

    @api_error_protect
    def update_workgroup_review_assessment(self, question_data):
        response = PUT(
            '{}/{}/{}/'.format(
                self._api_server_address,
                WORKGROUP_REVIEW_API,
                question_data['id']
            ),
            question_data
        )
        return json.loads(response.read())

    @api_error_protect
    def create_workgroup_review_assessment(self, question_data):
        response = POST(
            '{}/{}/'.format(
                self._api_server_address,
                WORKGROUP_REVIEW_API
            ),
            question_data
        )
        return json.loads(response.read())

    @api_error_protect
    def delete_workgroup_review_assessment(self, assessment_id):
        DELETE(
            '{}/{}/{}/'.format(
                self._api_server_address,
                WORKGROUP_REVIEW_API,
                assessment_id
            )
        )

    # TODO: this method post-process api response: probably they should be moved outside of this class
    def get_peer_review_items(self, reviewer_id, peer_id, group_id, content_id):
        group_peer_items = self.get_peer_review_items_for_group(group_id, content_id)
        return [pri for pri in group_peer_items if
                pri['reviewer'] == reviewer_id and (pri['user'] == peer_id or pri['user'] == int(peer_id))]

    # TODO: this method post-process api response: probably they should be moved outside of this class
    def get_user_peer_review_items(self, user_id, group_id, content_id):
        group_peer_items = self.get_peer_review_items_for_group(group_id, content_id)
        return [pri for pri in group_peer_items if pri['user'] == user_id or pri['user'] == int(user_id)]

    # TODO: this method pre-process api request: probably they should be moved outside of this class
    def submit_peer_review_items(self, reviewer_id, peer_id, group_id, content_id, data):
        # get any data already there
        current_data = {pi['question']: pi for pi in
                        self.get_peer_review_items(reviewer_id, peer_id, group_id, content_id)}
        for k, v in data.iteritems():
            if k in current_data:
                question_data = current_data[k]

                if question_data['answer'] != v:
                    if len(v) > 0:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = v

                        self.update_peer_review_assessment(question_data)
                    else:
                        self.delete_peer_review_assessment(question_data['id'])

            elif len(v) > 0:
                question_data = {
                    "question": k,
                    "answer": v,
                    "workgroup": group_id,
                    "user": peer_id,
                    "reviewer": reviewer_id,
                    "content_id": content_id,
                }
                self.create_peer_review_assessment(question_data)

    # TODO: this method post-process api response: probably they should be moved outside of this class
    def get_workgroup_review_items(self, reviewer_id, group_id, content_id):
        group_review_items = self.get_workgroup_review_items_for_group(group_id, content_id)
        return [gri for gri in group_review_items if gri['reviewer'] == reviewer_id and gri['content_id'] == content_id]

    # TODO: this method pre-process api request: probably they should be moved outside of this class
    def submit_workgroup_review_items(self, reviewer_id, group_id, content_id, data):
        # get any data already there
        current_data = {ri['question']: ri for ri in self.get_workgroup_review_items(reviewer_id, group_id, content_id)}
        for k, v in data.iteritems():
            if k in current_data:
                question_data = current_data[k]

                if question_data['answer'] != v:
                    if len(v) > 0:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = v

                        self.update_workgroup_review_assessment(question_data)
                    else:
                        self.delete_workgroup_review_assessment(question_data['id'])

            elif len(v) > 0:
                question_data = {
                    "question": k,
                    "answer": v,
                    "workgroup": group_id,
                    "reviewer": reviewer_id,
                    "content_id": content_id,
                }
                self.create_workgroup_review_assessment(question_data)

    @api_error_protect
    def get_workgroup_by_id(self, group_id):
        response = GET(
            '{}/{}/{}/'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id
            )
        )
        return json.loads(response.read())

    @api_error_protect
    def get_user_workgroup_for_course(self, user_id, course_id):
        qs_params = {
            "course_id": course_id,
        }
        response = GET(
            '{}/{}/{}/workgroups/?{}'.format(
                self._api_server_address,
                USERS_API,
                user_id,
                urlencode(qs_params),
            )
        )

        workgroups_list = json.loads(response.read())

        if workgroups_list['count'] < 1:
            return None

        return self.get_workgroup_by_id(workgroups_list['results'][0]['id'])

    @api_error_protect
    def get_user_details(self, user_id):
        response = GET(
            '{}/{}/{}'.format(
                self._api_server_address,
                USERS_API,
                user_id,
            )
        )
        return json.loads(response.read())

    @api_error_protect
    def get_user_grades(self, user_id, course_id):
        response = GET(
            '{}/{}/{}/courses/{}/grades'.format(
                self._api_server_address,
                USERS_API,
                user_id,
                course_id
            )
        )

        return json.loads(response.read())

    @api_error_protect
    def set_group_grade(self, group_id, course_id, activity_id, grade_value, max_grade):
        grade_data = {
            "course_id": course_id,
            "content_id": activity_id,
            "grade": grade_value,
            "max_grade": max_grade,
        }

        response = POST(
            '{}/{}/{}/grades/'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id
            ),
            grade_data
        )

        return json.loads(response.read())

    @api_error_protect
    def create_submission(self, submit_hash):
        response = POST(
            '{}/{}/'.format(
                self._api_server_address,
                SUBMISSION_API
            ),
            submit_hash
        )

        return json.loads(response.read())

    @api_error_protect
    def get_workgroup_submissions(self, group_id):
        response = GET(
            '{}/{}/{}/submissions/'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id,
            )
        )

        return json.loads(response.read())

    # TODO: this method post-process api response: probably they should be moved outside of this class
    def get_latest_workgroup_submissions_by_id(self, group_id):
        submission_list = self.get_workgroup_submissions(group_id)

        user_details_cache = {}

        def get_user_details(user_id):
            if user_id not in user_details_cache:
                user_details_cache[user_id] = self.get_user_details(user_id)
            return user_details_cache[user_id]

        submissions_by_id = {}
        for submission in submission_list:
            submission_id = submission['document_id']
            if submission['user']:
                submission[u'user_details'] = get_user_details(submission['user'])
            if submission_id in submissions_by_id:
                last_modified = build_date_field(submissions_by_id[submission_id]["modified"])
                this_modified = build_date_field(submission["modified"])
                if this_modified > last_modified:
                    submissions_by_id[submission["document_id"]] = submission
            else:
                submissions_by_id[submission["document_id"]] = submission

        return submissions_by_id

    @api_error_protect
    def get_review_assignment_groups(self, user_id, course_id, xblock_id):
        qs_params = {
            "course": course_id,
            "type": "reviewassignment",
            "data__xblock_id": xblock_id,
        }
        response = GET(
            '{}/{}/{}/groups/?{}'.format(
                self._api_server_address,
                USERS_API,
                user_id,
                urlencode(qs_params)
            )
        )

        return json.loads(response.read())["groups"]

    @api_error_protect
    def get_workgroups_for_assignment(self, assignment_id):
        response = GET(
            '{}/{}/{}/workgroups'.format(
                self._api_server_address,
                GROUP_API,
                assignment_id
            )
        )

        workgroups = json.loads(response.read())
        return workgroups["results"]

    @api_error_protect
    def get_group_detail(self, group_id):
        response = GET(
            '{}/{}/{}/'.format(
                self._api_server_address,
                GROUP_API,
                group_id
            )
        )

        return json.loads(response.read())

    @api_error_protect
    def get_workgroups_to_review(self, user_id, course_id, xblock_id):
        assignments = self.get_review_assignment_groups(user_id, course_id, xblock_id)

        workgroup_assignments = []
        for assignment in assignments:
            workgroup_assignments += self.get_workgroups_for_assignment(assignment["id"])

        return workgroup_assignments

    @api_error_protect
    def get_workgroup_reviewers(self, group_id):
        response = GET(
            '{}/{}/{}/groups'.format(
                self._api_server_address,
                WORKGROUP_API,
                group_id
            )
        )

        review_assignment_user_urls = ['{}{}users/'.format(self._api_server_address, ra["url"]) for ra in
                                       json.loads(response.read())]
        reviewers = []
        for users_url in review_assignment_user_urls:
            reviewers.extend(json.loads(GET(users_url).read())["users"])

        return reviewers

    @api_error_protect
    def mark_as_complete(self, course_id, content_id, user_id, stage=None):
        completion_data = {
            "content_id": content_id,
            "user_id": user_id,
        }

        if stage is not None:
            completion_data["stage"] = stage

        response = POST(
            '{}/{}/{}/completions/'.format(
                self._api_server_address,
                COURSES_API,
                course_id,
            ),
            completion_data
        )

        return json.loads(response.read())

    @api_error_protect
    def get_stage_completions(self, course_id, content_id, stage_id):
        qs_params = {
            "content_id": content_id,
            "stage": stage_id
        }

        response = GET(
            '{}/{}/{}/completions/?{}'.format(
                self._api_server_address,
                COURSES_API,
                course_id,
                urlencode(qs_params)
            )
        )

        return json.loads(response.read())['results']

    def get_stage_state(self, course_id, content_id, user_id, stage):
        user_workgroup = self.get_user_workgroup_for_course(user_id, course_id)
        if user_workgroup:
            users_in_group = {user['id'] for user in user_workgroup['users']}
        else:
            users_in_group = set()

        stage_completions = self.get_stage_completions(course_id, content_id, stage)
        if stage_completions:
            completed_users = {completion['user_id'] for completion in stage_completions}
        else:
            completed_users = set()

        return users_in_group, completed_users

    @api_error_protect
    def get_user_roles_for_course(self, user_id, course_id):
        qs_params = {
            "user_id": user_id,
        }
        response = GET(
            '{}/{}/{}/roles/?{}'.format(
                self._api_server_address,
                COURSES_API,
                course_id,
                urlencode(qs_params),
            )
        )

        return json.loads(response.read())


# Looks like it's an issue, but technically it's not; this code runs in LMS, so 127.0.0.1 is always correct
# location for API server, as it's basically executed in a neighbour thread/process/whatever.
api_server = "http://127.0.0.1:8000"
if hasattr(settings, 'API_LOOPBACK_ADDRESS'):
    api_server = settings.API_LOOPBACK_ADDRESS
project_api = ProjectAPI(api_server)

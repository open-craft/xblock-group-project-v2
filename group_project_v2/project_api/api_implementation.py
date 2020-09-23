from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import json
from six.moves.urllib.parse import urlencode

import itertools

from group_project_v2.api_error import api_error_protect
from group_project_v2.json_requests import DELETE, GET, PUT, POST
from group_project_v2.utils import memoize_with_expiration, build_date_field, is_absolute
from group_project_v2.project_api.dtos import (
    UserDetails, ProjectDetails, WorkgroupDetails, CompletionDetails,
    OrganisationDetails, UserGroupDetails
)

API_PREFIX = '/'.join(['api', 'server'])
WORKGROUP_API = '/'.join([API_PREFIX, 'workgroups'])
PEER_REVIEW_API = '/'.join([API_PREFIX, 'peer_reviews'])
WORKGROUP_REVIEW_API = '/'.join([API_PREFIX, 'workgroup_reviews'])
USERS_API = '/'.join([API_PREFIX, 'users'])
SUBMISSION_API = '/'.join([API_PREFIX, 'submissions'])
GROUP_API = '/'.join([API_PREFIX, 'groups'])
COURSES_API = '/'.join([API_PREFIX, 'courses'])
PROJECTS_API = '/'.join([API_PREFIX, 'projects'])
ORGANIZATIONS_API = '/'.join([API_PREFIX, 'organizations'])


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

    def build_url(self, url_parts, query_params=None, no_trailing_slash=False):
        url = "/".join([str(url_part) for url_part in url_parts])
        if not is_absolute(url):
            url = self._api_server_address + "/" + url
        if not no_trailing_slash:
            url += "/"
        if query_params:
            url += "?" + urlencode(query_params)

        return url

    @api_error_protect
    def _do_send_request(self, method, url, data=None):
        if self.dry_run:
            return {}

        if data is not None:
            response = method(url, data)
        else:
            response = method(url)

        # pylint: disable=comparison-with-callable
        if method == DELETE:
            return None

        return json.loads(response.read())

    def send_request(self, method, url_parts, data=None, query_params=None, no_trailing_slash=False):
        url = self.build_url(url_parts, query_params, no_trailing_slash)
        return self._do_send_request(method, url, data)

    @memoize_with_expiration()
    def get_user_organizations(self, user_id):
        qs_params = {'page_size': 0}
        return self.send_request(GET, (USERS_API, user_id, 'organizations'), query_params=qs_params)

    @memoize_with_expiration()
    def get_user_preferences(self, user_id):
        """ gets users preferences information """
        return self.send_request(GET, (USERS_API, user_id, 'preferences'), no_trailing_slash=True)

    def get_peer_review_items_for_group(self, group_id, content_id):
        qs_params = {"content_id": content_id}
        return self.send_request(GET, (WORKGROUP_API, group_id, 'peer_reviews'), query_params=qs_params)

    def update_peer_review_assessment(self, question_data):
        return self.send_request(PUT, (PEER_REVIEW_API, question_data['id']), data=question_data)

    def create_peer_review_assessment(self, question_data):
        return self.send_request(POST, (PEER_REVIEW_API,), data=question_data)

    def delete_peer_review_assessment(self, assessment_id):
        self.send_request(DELETE, (PEER_REVIEW_API, assessment_id))

    # Do not cache - used both in submitting review and calculating grade, so if this call is cached grade calculation
    # sees old value. So, when last review is performed, grade calculation does not see it and returns "No grade yet".
    # See MCKIN-3501 and MCKIN-3471 for what would happen than.
    def get_workgroup_review_items_for_group(self, group_id, content_id):
        qs_params = {"content_id": content_id}
        return self.send_request(GET, (WORKGROUP_API, group_id, 'workgroup_reviews'), query_params=qs_params)

    def create_workgroup_review_assessment(self, question_data):
        return self.send_request(POST, (WORKGROUP_REVIEW_API, ), data=question_data)

    def update_workgroup_review_assessment(self, question_data):
        return self.send_request(PUT, (WORKGROUP_REVIEW_API, question_data['id']), data=question_data)

    def delete_workgroup_review_assessment(self, assessment_id):
        self.send_request(DELETE, (WORKGROUP_REVIEW_API, assessment_id))

    def get_user_grades(self, user_id, course_id):
        return self.send_request(GET, (USERS_API, user_id, 'courses', course_id, 'grades'), no_trailing_slash=True)

    def set_group_grade(self, group_id, course_id, activity_id, grade_value, max_grade):
        grade_data = {
            "course_id": str(course_id),
            "content_id": activity_id,
            "grade": grade_value,
            "max_grade": max_grade,
        }

        return self.send_request(POST, (WORKGROUP_API, group_id, 'grades'), data=grade_data)

    def create_submission(self, submit_hash):
        return self.send_request(POST, (SUBMISSION_API, ), data=submit_hash)

    # Do not cache - Upload submission handler updates a list of submissions, than queries which submissions are there
    def get_workgroup_submissions(self, group_id):
        return self.send_request(GET, (WORKGROUP_API, group_id, 'submissions'))

    @memoize_with_expiration()
    def get_review_assignment_groups(self, user_id, course_id, xblock_id):
        qs_params = {
            "course": course_id,
            "type": "reviewassignment",
            "data__xblock_id": xblock_id,
        }
        response = self.send_request(GET, (USERS_API, user_id, 'groups'), query_params=qs_params)
        return response.get("groups", {})

    def get_group_detail(self, group_id):
        return self.send_request(GET, (GROUP_API, group_id))

    # TODO: methods below post-process api response - they should be moved outside of this class.
    # When doing the move, add tests before moving, since there are no test coverage for them
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

    # TODO: these two methods are a different filters on top of the same method - might make sense to combine them
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
        for question_id, answer in data.items():
            if question_id in current_data:
                question_data = current_data[question_id]

                if question_data['answer'] != answer:
                    if answer:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = answer

                        self.update_peer_review_assessment(question_data)
                    else:
                        self.delete_peer_review_assessment(question_data['id'])

            elif answer:
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
        for question_id, answer in data.items():
            if question_id in current_data:
                question_data = current_data[question_id]

                if question_data['answer'] != answer:
                    if answer:
                        # update with relevant data
                        del question_data['created']
                        del question_data['modified']
                        question_data['answer'] = answer

                        self.update_workgroup_review_assessment(question_data)
                    else:
                        self.delete_workgroup_review_assessment(question_data['id'])

            elif answer:
                question_data = {
                    "question": question_id,
                    "answer": answer,
                    "workgroup": group_id,
                    "reviewer": reviewer_id,
                    "content_id": content_id,
                }
                self.create_workgroup_review_assessment(question_data)


class TypedProjectAPI(ProjectAPI):
    """
    This class is intended to contain methods that return typed responses.
    Some of the methods may return non-reentrant iterables (i.e. generators) - clients are responsible to
    convert them to reentrant collection if need more than one pass over the response
    """
    def _consume_paged_response(self, method, entry_url, data=None):
        next_page_url = entry_url

        while next_page_url:
            response = self._do_send_request(method, next_page_url, data)
            for item in response['results']:
                yield item

            next_page_url = response.get('next')

    @memoize_with_expiration()
    def get_user_details(self, user_id):
        """
        :param int user_id: User ID
        :rtype: UserDetails
        """
        response = self.send_request(GET, (USERS_API, user_id), no_trailing_slash=True)
        return UserDetails(**response)

    @memoize_with_expiration()
    def get_project_by_content_id(self, course_id, content_id):
        """
        :param str course_id: Course ID
        :param str content_id: Content ID
        :rtype: ProjectDetails
        """
        query_params = {
            'content_id': content_id,
            'course_id': course_id
        }
        response = self.send_request(GET, (PROJECTS_API,), query_params=query_params)
        assert len(response['results']) <= 1
        if not response['results']:
            return None

        project = response['results'][0]
        return ProjectDetails(**project)

    @memoize_with_expiration()
    def get_project_details(self, project_id):
        """
        :param int project_id: Project ID
        :rtype: ProjectDetails
        """
        response = self.send_request(GET, (PROJECTS_API, project_id), no_trailing_slash=True)
        return ProjectDetails(**response)

    @memoize_with_expiration()
    def get_workgroup_by_id(self, group_id):
        """
        :param int group_id: Group ID
        :rtype: WorkgroupDetails
        """
        response = self.send_request(GET, (WORKGROUP_API, group_id))
        return WorkgroupDetails(**response)

    @memoize_with_expiration()
    def get_user_workgroup_for_course(self, user_id, course_id):
        """
        :param int user_id: User ID
        :param str course_id: Course ID
        :rtype: WorkgroupDetails
        """
        qs_params = {"course_id": course_id}
        workgroups_list = self.send_request(GET, (USERS_API, user_id, 'workgroups'), query_params=qs_params)

        if not workgroups_list or workgroups_list['count'] < 1:
            return None

        return self.get_workgroup_by_id(workgroups_list['results'][0]['id'])

    # No caching here - can be updated mid-request
    def get_completions_by_content_id(self, course_id, content_id):
        """
        :param str course_id: course ID
        :param str content_id: content ID
        :rtype: collections.Iterable[CompletionDetails]
        """
        query_parameters = {
            'content_id': content_id
        }
        url = self.build_url((COURSES_API, course_id, 'completions'), query_params=query_parameters)

        for item in self._consume_paged_response(GET, url):
            yield CompletionDetails(**item)

    # TODO: add tests
    @memoize_with_expiration()
    def get_workgroups_for_assignment(self, assignment_id):
        """
        :param int assignment_id: Assignment ID
        :rtype: list[WorkgroupDetails]
        """
        workgroups = self.send_request(GET, (GROUP_API, assignment_id, 'workgroups'), no_trailing_slash=True)
        return [WorkgroupDetails(**item) for item in workgroups["results"]]

    # TODO: add tests
    def get_workgroups_to_review(self, user_id, course_id, xblock_id):
        """
        :param int user_id: User ID
        :param str course_id: Course ID
        :param str xblock_id: Block ID
        :rtype: list[WorkgroupDetails]
        """
        assignments = self.get_review_assignment_groups(user_id, course_id, xblock_id)

        return list(
            itertools.chain.from_iterable(
                self.get_workgroups_for_assignment(assignment["id"])
                for assignment in assignments
            )
        )

    # TODO: make typed + add tests
    def get_latest_workgroup_submissions_by_id(self, group_id):
        """
        :param int group_id: Group ID
        :rtype: dict[dict]
        """
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

    # TODO: add tests + do something about different type of user_details.organization attribute
    def get_member_data(self, user_id):
        """
        :param int user_id:
        :rtype: UserDetails
        """
        user_details = self.get_user_details(user_id)  # user_details.organization is an int here
        user_organizations = self.get_user_organizations(user_id)
        if user_organizations:
            user_details.organization = user_organizations[0]['display_name']  # and a string here
        return user_details

    @memoize_with_expiration()
    def get_user_roles_for_course(self, user_id, course_id):
        """
        Returns role names user has for a given course.

        :param int user_id: User Id
        :param int course_id: Course id

        :rtype: set[str]
        """

        qs_params = {
            "user_id": user_id,
        }
        response = self.send_request(GET, (COURSES_API, course_id, 'roles'), query_params=qs_params)
        return set(role['role'] for role in response)

    @memoize_with_expiration()
    def get_organization_by_id(self, org_id):
        """
        :param org_id:
        :return: Requested organization
        :rtype: OrganisationDetails
        """
        return OrganisationDetails(**self.send_request(GET, (ORGANIZATIONS_API, org_id)))

    def get_user_permissions(self, user_id):
        return self.get_user_groups(user_id, "permission")

    @memoize_with_expiration()
    def get_user_groups(self, user_id, group_type=None):
        """
        :param user_id: User id
        :param str group_type: Optional filter for group type. Defults to None,
                               which means no filter.
        :return: List of UserGroupDetails
        :rtype: Iterable[UserGroupDetails]
        """
        data = {}
        if group_type is not None:
            data = {
                "type": group_type
            }

        response_json = self.send_request(GET, (USERS_API, user_id, 'groups'), query_params=data)
        list_of_groups = response_json['groups']
        return list(UserGroupDetails(**group_dict) for group_dict in list_of_groups)

from past.builtins import basestring
from builtins import object
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse

import mock
from mock import Mock
from selenium.webdriver.support.wait import WebDriverWait
from xblockutils.resources import ResourceLoader

from group_project_v2.api_error import ApiError
from group_project_v2.mixins import UserAwareXBlockMixin, AuthXBlockMixin
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import UserDetails, WorkgroupDetails
from group_project_v2.stage_components import GroupProjectReviewQuestionXBlock

loader = ResourceLoader(__name__)  # pylint: disable=invalid-name


class TestConstants(object):
    class Users(object):
        USER1_ID = 1
        USER2_ID = 2
        USER3_ID = 3

        UNKNOWN_USER = 200

    class Groups(object):
        GROUP1_ID = 1
        GROUP2_ID = 2
        GROUP3_ID = 3


KNOWN_USERS = {
    TestConstants.Users.USER1_ID: UserDetails(
        id=TestConstants.Users.USER1_ID, email="jane@example.com",
        is_active=True, username="Jane", full_name="Jane"
    ),
    TestConstants.Users.USER2_ID: UserDetails(
        id=TestConstants.Users.USER2_ID, email="jack@example.com",
        is_active=True, username="Jack", full_name="Jack"
    ),
    TestConstants.Users.USER3_ID: UserDetails(
        id=TestConstants.Users.USER3_ID, email="jill@example.com",
        is_active=True, username="Jill", full_name="Jill"
    ),
}

WORKGROUP = WorkgroupDetails(**{
    "id": TestConstants.Groups.GROUP1_ID,
    "name": "Group 1",
    "project": 1,
    "groups": [],
    "users": [
        {"id": user.id, "username": user.username, "email": user.email}
        for user in KNOWN_USERS.values()
    ],
    "submissions": [],
    "workgroup_reviews": [],
    "peer_reviews": []
})

OTHER_GROUPS = {
    TestConstants.Groups.GROUP2_ID: WorkgroupDetails(id=TestConstants.Groups.GROUP2_ID, name="Group 2"),
    TestConstants.Groups.GROUP3_ID: WorkgroupDetails(id=TestConstants.Groups.GROUP3_ID, name="Group 3"),
}


def make_submission_data(doc_url, doc_filename, upload_date, user_details):
    return {
        'document_url': doc_url,
        'document_filename': doc_filename,
        'modified': upload_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'user_details': user_details
    }


def _get_user_details(user_id):
    if user_id not in KNOWN_USERS:
        raise ApiError("User {user_id} not found".format(user_id=user_id))
    return KNOWN_USERS[user_id]


def get_mock_project_api():
    """ Mock api with canned responses """
    mock_api = Mock(spec=TypedProjectAPI)
    mock_api.get_user_preferences = Mock(return_value={})
    mock_api.get_user_workgroup_for_course = Mock(return_value=WORKGROUP)
    mock_api.get_workgroup_by_id = Mock(return_value=WORKGROUP)
    mock_api.get_stage_state = Mock(return_value=({1, 2}, set()))
    mock_api.get_user_details = Mock(side_effect=_get_user_details)
    mock_api.get_workgroups_to_review = Mock(return_value={})
    mock_api.get_latest_workgroup_submissions_by_id = Mock(return_value={})
    mock_api.get_user_peer_review_items = Mock(return_value={})
    mock_api.get_peer_review_items_for_group = Mock(return_value={})
    mock_api.get_workgroup_review_items = Mock(return_value={})
    mock_api.get_workgroup_review_items_for_group = Mock(return_value={})
    mock_api.get_user_organizations = Mock(
        return_value=[{'display_name': "Org1", "id": 1}])
    mock_api.get_workgroup_reviewers = Mock(return_value={})
    mock_api.get_member_data = Mock(side_effect=_get_user_details)
    mock_api.get_user_groups = Mock(return_value=tuple())
    mock_api.get_user_permissions = Mock(return_value=tuple())
    mock_api.get_user_roles_for_course = Mock(return_value=set())

    return mock_api


class TestWithPatchesMixin(object):
    def make_patch(self, obj, member_name, new=mock.DEFAULT):
        patcher = mock.patch.object(obj, member_name, new)
        patch_instance = patcher.start()
        self.addCleanup(patcher.stop)
        return patch_instance


def make_api_error(code, reason):
    error_mock = mock.Mock()
    error_mock.code = code
    error_mock.reason = reason
    return ApiError(error_mock)


def raise_api_error(code, reason):
    raise make_api_error(code, reason)


def make_review_item(reviewer, question, peer=None, content_id=None, answer=None, group=None):
    return {
        'reviewer': reviewer, 'question': question, 'content_id': content_id, 'answer': answer,
        'user': peer, 'workgroup': group
    }


def make_question(question_id, title):
    question = mock.create_autospec(GroupProjectReviewQuestionXBlock)
    question.question_id = question_id
    question.title = title
    return question


def switch_to_ta_grading(project_api_mock, review_group_id=1):
    project_api_mock.get_user_preferences.return_value = {
        UserAwareXBlockMixin.TA_REVIEW_KEY: review_group_id
    }
    project_api_mock.get_user_roles_for_course.return_value = set(
        AuthXBlockMixin.DEFAULT_TA_ROLE)


def make_workgroup(workgroup_id, users=None):
    if not users:
        users = []
    return WorkgroupDetails(id=workgroup_id, users=users)


@contextmanager
def expect_new_browser_window(browser, timeout=30):
    old_window_handle = browser.current_window_handle

    def new_window_available(brwsr):
        handles = brwsr.window_handles
        return any(handle != old_window_handle for handle in handles)

    yield
    WebDriverWait(browser, timeout).until(
        new_window_available, message="No window was opened")


@contextmanager
def switch_to_other_window(browser, other_window):
    old_window_handle = browser.current_window_handle
    browser.switch_to_window(other_window)
    yield
    browser.switch_to_window(old_window_handle)


def get_other_windows(browser):
    current_window_handle = browser.current_window_handle
    return [handle for handle in browser.window_handles if handle != current_window_handle]


def parse_datetime(datetime_string):
    return (
        datetime.strptime(datetime_string.split(".")[0], "%Y-%m-%d %H:%M:%S")
        if isinstance(datetime_string, basestring) else None
    )


# pylint:disable=no-self-use
class MockedAuthXBlockMixin(AuthXBlockMixin):

    @property
    def ta_roles(self):
        return self.DEFAULT_TA_ROLE

    @property
    def user_id(self):
        return 0

    @property
    def see_dashboard_role_perms(self):
        return []

    @property
    def see_dashboard_for_all_orgs_perms(self):
        return []


def _get_url_info(url):
    parsed_url = urlparse(url)
    url_path = parsed_url.path
    url_query = set(parsed_url.query.split("&"))
    return url_path, url_query


def find_url(url, urls):
    main_url_path, main_url_query = _get_url_info(url)
    for url_check in urls:
        check_url_path, check_url_query = _get_url_info(url_check)
        if check_url_path == main_url_path and check_url_query == main_url_query:
            return url_check
    return None

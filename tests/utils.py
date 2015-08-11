from mock import Mock
import mock
from xblockutils.resources import ResourceLoader
from group_project_v2.api_error import ApiError

from group_project_v2.project_api import ProjectAPI, UserDetails


loader = ResourceLoader(__name__)  # pylint: disable=invalid-name

KNOWN_USERS = {
    1: UserDetails(**{
        "id": 1, "email": "jane@example.com", "is_active": True,
        "username": "Jane", "full_name": "Jane", "resources": []
    }),
    2: UserDetails(**{
        "id": 2, "email": "jack@example.com", "is_active": True,
        "username": "Jack", "full_name": "Jack", "resources": []
    }),
    3: UserDetails(**{
        "id": 3, "email": "jill@example.com", "is_active": True,
        "username": "Jill", "full_name": "Jill", "resources": []
    })
}

WORKGROUP = {
    "id": 1,
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
}

OTHER_GROUPS = {
    2: {"id": 2, "name": "Group 2"},
    3: {"id": 3, "name": "Group 3"},
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
    mock_api = Mock(spec=ProjectAPI)
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
    mock_api.get_user_organizations = Mock(return_value=[{'display_name': "Org1"}])
    mock_api.get_workgroup_reviewers = Mock(return_value={})

    mock_api.mark_as_complete = Mock(return_value={})
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

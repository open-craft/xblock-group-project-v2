from mock import Mock
from xblockutils.resources import ResourceLoader
from group_project_v2.api_error import ApiError

import group_project_v2.project_api as project_api_module


loader = ResourceLoader(__name__)

KNOWN_USERS = {
    1: {
        "id": 1, "email": "jane@example.com", "is_active": True,
        "username": "Jane", "full_name": "Jane", "resources": []
    },
    2: {
        "id": 2, "email": "jack@example.com", "is_active": True,
        "username": "Jack", "full_name": "Jack", "resources": []
    }
}

def _get_user_details(user_id):
    if user_id not in KNOWN_USERS:
        raise ApiError("User {user_id} not found".format(user_id=user_id))
    return KNOWN_USERS[user_id]


def get_mock_project_api():
    """ Mock api with canned responses """
    mock_api = Mock(spec=project_api_module.ProjectAPI)
    mock_api.get_user_preferences = Mock(return_value={})
    mock_api.get_user_workgroup_for_course = Mock(return_value={
        "id": 1,
        "name": "Group 1",
        "project": 1,
        "groups": [],
        "users": [
            {"id": 1, "username": "Jane", "email": "jane@example.com"},
            {"id": 2, "username": "Jack", "email": "jack@example.com"}
        ],
        "submissions": [],
        "workgroup_reviews": [],
        "peer_reviews": []
    })
    mock_api.get_stage_state = Mock(return_value=({1, 2}, set()))
    mock_api.get_user_details = Mock(side_effect=_get_user_details)
    mock_api.get_workgroups_to_review = Mock(return_value={})
    return mock_api

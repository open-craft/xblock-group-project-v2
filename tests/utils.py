import datetime
import textwrap
from mock import Mock
from xblockutils.resources import ResourceLoader
from group_project_v2.api_error import ApiError

import group_project_v2.project_api as project_api_module
from group_project_v2.utils import format_date

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
    mock_api.get_latest_workgroup_submissions_by_id = Mock(return_value={})
    return mock_api


def get_open_close_label(open_date, close_date):
    if not open_date and not close_date:
        return None

    today = datetime.datetime.today()
    before_open = open_date and today < open_date
    after_close = close_date and today > close_date

    if before_open:
        label = "opens"
    elif after_close:
        label = "closed on"
    else:
        label = "due"

    return "{label} {date}".format(label=label, date=format_date(today))


COMPLEX_CONTENTS_SENTINEL = "complex_content"

class XMLContents(object):
    COMPLEX_CONTENTS_SENTINEL = COMPLEX_CONTENTS_SENTINEL

    class Example1(object):
        ACTIVITIES = ("Activity 1", "Activity 2")
        STAGES = ('overview', 'upload', 'peer_review', 'group_review', 'peer_assessment', 'group_assessment')

        STAGE_DATA = {
            'overview': {
                'title': 'Overview',
                'contents': "<p>I'm overview Stage</p>",
            },
            'upload': {
                'title': 'Upload',
                'close_date': datetime.date(2014, 5, 24),
                'contents': "<p>I'm overview Stage</p>",
            },
            'peer_review': {
                'title': 'Review Team',
                'open_data': datetime.date(2014, 5, 24),
                'close_date': datetime.date(2014, 6, 20),
                "contents": COMPLEX_CONTENTS_SENTINEL,
            },
            'group_review': {
                'title': 'Review Group',
                'open_data': datetime.date(2014, 5, 24),
                'close_date': datetime.date(2014, 6, 20),
                "contents": COMPLEX_CONTENTS_SENTINEL,
            },
            'peer_assessment': {
                'title': 'Evaluate Team Feedback',
                'open_data': datetime.date(2014, 6, 20),
                "contents": COMPLEX_CONTENTS_SENTINEL,
            },
            'group_assessment': {
                'title': 'Evaluate Group Feedback',
                'open_data': datetime.date(2014, 6, 20),
                "contents": COMPLEX_CONTENTS_SENTINEL,
            },
        }

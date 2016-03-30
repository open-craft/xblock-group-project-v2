
from unittest import TestCase

import mock
from group_project_v2.json_requests import GET

from group_project_v2.project_api import api_implementation
from tests.utils import TestWithPatchesMixin


class BaseApiTest(TestCase, TestWithPatchesMixin):

    def request_side_effect(self):
        return self.next_request_response

    def setUp(self):
        self.next_request_response = {}
        self.project_api = api_implementation.TypedProjectAPI("http:/foo.bar:8000")
        self.project_api.send_request = mock.MagicMock(side_effect=lambda *args, **kwargs: self.next_request_response)

    def test_get_user_roles_for_course(self):
        user_id = 1234
        course_id = 4321
        self.next_request_response = [
            {'role': 'foo', 'id': user_id},
            {'role': 'bar', 'id': user_id},
            {'role': 'baz', 'id': user_id},
        ]
        response = self.project_api.get_user_roles_for_course(user_id, course_id)
        self.assertEqual(response, {'foo', 'bar', 'baz'})
        self.project_api.send_request.assert_called_once_with(
            GET, ('api/server/courses', course_id, 'roles'), query_params={'user_id': user_id}
        )

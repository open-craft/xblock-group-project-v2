import json
from unittest import TestCase

import ddt
import mock
from mock.mock import call

from group_project_v2.json_requests import GET
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.api_implementation import WORKGROUP_API, PROJECTS_API
from tests.utils import TestWithPatchesMixin, make_review_item as mri


class CannedResponses(object):
    class Projects(object):
        project1 = {
            "id": 1,
            "url": "/api/server/projects/1/",
            "created": None, "modified": None,
            "course_id": "McKinsey/GP2/T2",
            "content_id": "i4x://McKinsey/GP2/gp-v2-project/abcdefghijklmnopqrstuvwxyz12345",
            "organization": "Org1",
            "workgroups": [1, 2, 3]
        }
        project2 = {
            "id": 2,
            "url": "/api/server/projects/2/",
            "created": "2015-08-04T13:26:01Z", "modified": "2015-08-04T13:26:01Z",
            "course_id": "McKinsey/GP2/T1",
            "content_id": "i4x://McKinsey/GP2/gp-v2-project/41fe8cae0614470c9aeb72bd078b0348",
            "organization": None,
            "workgroups": [20, 21, 22]
        }

    class Workgroups(object):
        workgroup1 = {
            "id": 20,
            "url": "/api/server/workgroups/20/",
            "created": "2015-11-05T12:20:10Z", "modified": "2015-11-13T11:07:58Z",
            "name": "Group 1",
            "project": 2,
            "groups": [
                {
                    "id": 54,
                    "url": "/api/server/groups/54/",
                    "name": "Assignment group for 20",
                    "type": "reviewassignment",
                    "data": {
                        "xblock_id": "i4x://McKinsey/GP2/gp-v2-activity/ddf65290008d48c991ec41f724877d90",
                        "assignment_date": "2015-11-05T12:45:10.870070Z"
                    }
                }
            ],
            "users": [
                {"id": 17, "url": "/user_api/v1/users/17/", "username": "Alice", "email": "Alice@example.com"},
                {"id": 20, "url": "/user_api/v1/users/20/", "username": "Derek", "email": "Derek@example.com"}
            ],
            "submissions": [1, 2, 3],
            "workgroup_reviews": [4, 5, 6],
            "peer_reviews": [7, 8, 9]
        }
        workgroup2 = {
            "id": 21,
            "url": "http://localhost:8000/api/server/workgroups/21/",
            "created": "2015-11-05T12:20:18Z", "modified": "2015-11-05T12:45:13Z",
            "name": "Group 2",
            "project": 1,
            "groups": [
                {
                    "id": 55,
                    "url": "http://localhost:8000/api/server/groups/55/",
                    "name": "Assignment group for 21",
                    "type": "reviewassignment",
                    "data": {
                        "xblock_id": "i4x://McKinsey/GP2/gp-v2-activity/ddf65290008d48c991ec41f724877d90",
                        "assignment_date": "2015-11-05T12:45:12.563121Z"
                    }
                }
            ],
            "users": [
                {"id": 18, "url": "/user_api/v1/users/18/", "username": "Bob", "email": "Bob@example.com"}
            ],
            "submissions": [10, 11],
            "workgroup_reviews": [117, 118, 119, 120, 135],
            "peer_reviews": [1111, 1121, 111011]
        }

    class Completions(object):
        non_paged = {
            "count": 5,
            "next": None,
            "previous": None,
            "num_pages": 1,
            "results": [
                {
                    "id": 306, "user_id": 22, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
                },
                {
                    "id": 307, "user_id": 23, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
                {
                    "id": 308, "user_id": 24, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
                {
                    "id": 309, "user_id": 25, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
                {
                    "id": 310, "user_id": 26, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:31:20Z", "modified": "2015-11-17T10:31:20Z"
                },
            ]
        }

        paged_page1 = {
            "count": 3,
            "next": "http://localhost:8000/api/server/courses/McKinsey/GP2/T1/completions?page=2&page_size=3",
            "previous": None,
            "num_pages": 3,
            "results": [
                {
                    "id": 306, "user_id": 22, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
                },
                {
                    "id": 307, "user_id": 23, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
                {
                    "id": 308, "user_id": 24, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
            ]
        }
        paged_page2 = {
            "count": 3,
            "next": "http://localhost:8000/api/server/courses/McKinsey/GP2/T1/completions?page=3&page_size=3",
            "previous": "http://localhost:8000/api/server/courses/McKinsey/GP2/T1/completions?page=1&page_size=3",
            "num_pages": 3,
            "results": [
                {
                    "id": 306, "user_id": 25, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
                },
                {
                    "id": 307, "user_id": 26, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
                {
                    "id": 308, "user_id": 27, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                },
            ]
        }
        paged_page3 = {
            "count": 3,
            "next": None,
            "previous": "http://localhost:8000/api/server/courses/McKinsey/GP2/T1/completions?page=2&page_size=3",
            "num_pages": 3,
            "results": [
                {
                    "id": 306, "user_id": 28, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
                },
                {
                    "id": 307, "user_id": 29, "course_id": "McKinsey/GP2/T1", "stage": None,
                    "content_id": "i4x://McKinsey/GP2/gp-v2-stage-grade-display/8520b55c95684ff6b9c2a9129c126f0b",
                    "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
                }
            ]
        }


@ddt.ddt
class TestProjectApi(TestCase, TestWithPatchesMixin):
    api_server_address = 'http://localhost/api'

    def setUp(self):
        self.project_api = TypedProjectAPI(self.api_server_address, dry_run=False)

    def _patch_send_request(self, calls_and_results, missing_callback=None):
        # pylint: disable=unused-argument
        def side_effect(method, url_parts, data=None, query_params=None, no_trailing_slash=False):
            if url_parts in calls_and_results:
                return calls_and_results[url_parts]
            if 'default' in calls_and_results:
                return calls_and_results['default']
            if missing_callback:
                return missing_callback(url_parts)
            return None

        return mock.patch.object(self.project_api, 'send_request', mock.Mock(side_effect=side_effect))

    def _patch_do_send_request(self, urls_and_results, missing_callback=None):
        def side_effect(method, url, data=None):
            if url in urls_and_results:
                return urls_and_results[url]
            if 'default' in urls_and_results:
                return urls_and_results['default']
            if missing_callback:
                return missing_callback(url)
            return None

        return mock.patch.object(self.project_api, '_do_send_request', mock.Mock(side_effect=side_effect))

    @ddt.data(
        (["part1", "part2"], None, False, api_server_address+"/part1/part2/", {'error': True}),
        (["part1", "part2"], None, True, api_server_address+"/part1/part2", {'success': True}),
        (["part1", "part2", "part3"], None, False, api_server_address+"/part1/part2/part3/", {'error': True}),
        (["part1"], {'qwe': 'rty'}, False, api_server_address+"/part1/?qwe=rty", {'success': True, 'data': [1, 2, 3]}),
        (["part1"], {'qwe': 'rty', 'asd': 'zxc'}, False, api_server_address+"/part1/?qwe=rty&asd=zxc", {}),
        (["part1"], {'qwe': 'rty', 'asd': 'zxc'}, True, api_server_address+"/part1?qwe=rty&asd=zxc", {}),
    )
    @ddt.unpack
    def test_send_request_no_data(self, url_parts, query_params, no_trailing_slash, expected_url, expected_response):
        response = mock.Mock()
        response.read.return_value = json.dumps(expected_response)

        method = mock.Mock(return_value=response)
        result = self.project_api.send_request(
            method, url_parts, query_params=query_params, no_trailing_slash=no_trailing_slash
        )
        method.assert_called_once_with(expected_url)
        self.assertEqual(result, expected_response)

    # pylint: disable=too-many-arguments
    @ddt.data(
        (["part1", "part2"], None, [123], False, api_server_address+"/part1/part2/", {'error': True}),
        (["part1", "part2"], None, 'qwerty', True, api_server_address+"/part1/part2", {'success': True}),
        (
                ["part1", "part2", "part3"], None, {'data': 11}, False,
                api_server_address+"/part1/part2/part3/", {'error': True}
        ),
        (
                ["part1"], {'qwe': 'rty'}, {'var1': 1, 'var2': 2}, False,
                api_server_address+"/part1/?qwe=rty", {'success': True, 'data': [1, 2, 3]}
        ),
        (
                ["part1"], {'qwe': 'rty', 'asd': 'zxc'}, {'stage': 1, 'activity': 2}, False,
                api_server_address+"/part1/?qwe=rty&asd=zxc", {}
        ),
        (
                ["part1"], {'qwe': 'rty', 'asd': 'zxc'}, {'data': None}, True,
                api_server_address+"/part1?qwe=rty&asd=zxc", {}
        ),
    )
    @ddt.unpack
    def test_send_request_with_data(
            self, url_parts, query_params, data, no_trailing_slash, expected_url, expected_response
    ):
        response = mock.Mock()
        response.read.return_value = json.dumps(expected_response)

        method = mock.Mock(return_value=response)
        result = self.project_api.send_request(
            method, url_parts, data=data, query_params=query_params, no_trailing_slash=no_trailing_slash
        )
        method.assert_called_once_with(expected_url, data)
        self.assertEqual(result, expected_response)

    def test_dry_run_does_not_send_request(self):
        method = mock.Mock()
        proj_api = TypedProjectAPI(self.api_server_address, True)
        result = proj_api.send_request(method, ('123', '34'))
        method.assert_not_called()
        self.assertEqual(result, {})

    def test_send_delete_request_returns_none(self):
        with mock.patch('group_project_v2.project_api.api_implementation.DELETE') as patched_delete:
            result = self.project_api.send_request(patched_delete, ('123', '456'))
            self.assertEqual(result, None)

            patched_delete.assert_called_once_with(self.api_server_address+'/123/456/')

    @ddt.data(
        ('user1', 'course1', 'xblock:block-1', []),
        ('user1', 'course1', 'xblock:block-1', [1, 5]),
        ('user2', 'course-2', 'xblock:html-block-1', [1, 5, 6]),
        ('user7', 'course-15', 'xblock:construction-block-743', [6, 10, 15]),
    )
    @ddt.unpack
    def test_get_workgroups_to_review(self, user_id, course_id, xblock_id, assignment_ids):
        def assignment_data_by_id(a_id):
            return {"id": a_id, 'data': 'data'+str(a_id)}

        with mock.patch.object(self.project_api, 'get_review_assignment_groups') as review_assignment_groups, \
                mock.patch.object(self.project_api, 'get_workgroups_for_assignment') as workgroups_for_assignment:

            review_assignment_groups.return_value = [{"id": assignment_id} for assignment_id in assignment_ids]
            workgroups_for_assignment.side_effect = lambda a_id: [assignment_data_by_id(a_id)]

            response = self.project_api.get_workgroups_to_review(user_id, course_id, xblock_id)

            review_assignment_groups.assert_called_once_with(user_id, course_id, xblock_id)
            self.assertEqual(
                workgroups_for_assignment.mock_calls,
                [mock.call(assignment_id) for assignment_id in assignment_ids]
            )

            self.assertEqual(response, [assignment_data_by_id(assignment_id) for assignment_id in assignment_ids])

    @ddt.data(
        (1, 'content1', [], []),
        (2, 'content2', [{'data': {'xblock_id': 'content2'}, 'url': 'url1'}], ['url1']),
        (
            3, 'content3',
            [
                {'data': {'xblock_id': 'content2'}, 'url': 'url1'},
                {'data': {'xblock_id': 'content3'}, 'url': 'url2'},
                {'data': {'xblock_id': 'content3'}, 'url': 'url3'}
            ],
            ['url2', 'url3']
        ),
    )
    @ddt.unpack
    def test_workgroup_reviewers(self, group_id, content_id, review_assignments, expected_urls):
        calls_and_results = {
            (WORKGROUP_API, group_id, 'groups'): review_assignments
        }

        def missing_callback(url_parts):  # pylint: disable=unused-argument
            return {'users': [1, 2, 3]}

        with self._patch_send_request(calls_and_results, missing_callback) as patched_send_request:
            response = self.project_api.get_workgroup_reviewers(group_id, content_id)

            self.assertEqual(
                patched_send_request.mock_calls,
                [mock.call(GET, (WORKGROUP_API, group_id, 'groups'), no_trailing_slash=True)] +
                [mock.call(GET, (expected_url, 'users')) for expected_url in expected_urls]
            )

            self.assertEqual(response, [1, 2, 3] * len(expected_urls))

    @ddt.data(
        (1, 2, [mri(1, 'qwe', peer=2), mri(1, 'asd', peer=3)], [mri(1, 'qwe', peer=2)]),
        (
            5, 3,
            [mri(5, 'qwe', peer=3), mri(5, 'asd', peer=3)],
            [mri(5, 'qwe', peer=3), mri(5, 'asd', peer=3)]
        ),
        (11, 12, [mri(11, 'qwe', peer=3), mri(11, 'asd', peer=4)], []),
        (11, 12, [mri(15, 'qwe', peer=12), mri(18, 'asd', peer=12)], []),
    )
    @ddt.unpack
    def test_get_peer_review_items(self, reviewer_id, peer_id, review_items, expected_result):
        with mock.patch.object(self.project_api, 'get_peer_review_items_for_group') as patched_get_review_items:
            patched_get_review_items.return_value = review_items
            result = self.project_api.get_peer_review_items(reviewer_id, peer_id, 'group_id', 'content_id')

            self.assertEqual(result, expected_result)
            patched_get_review_items.assert_called_once_with('group_id', 'content_id')

    @ddt.data(
        (1, [mri(2, 'qwe', peer=1), mri(5, 'asd', peer=1)], [mri(2, 'qwe', peer=1), mri(5, 'asd', peer=1)]),
        (5, [mri(7, 'qwe', peer=5), mri(7, 'asd', peer=5)], [mri(7, 'qwe', peer=5), mri(7, 'asd', peer=5)]),
        (11, [mri(16, 'qwe', peer=3), mri(18, 'asd', peer=4)], []),
        (11, [mri(16, 'qwe', peer=3), mri(18, 'question1', peer=11)], [mri(18, 'question1', peer=11)]),
    )
    @ddt.unpack
    def test_get_user_peer_review_items(self, user_id, review_items, expected_result):
        with mock.patch.object(self.project_api, 'get_peer_review_items_for_group') as patched_get_review_items:
            patched_get_review_items.return_value = review_items
            result = self.project_api.get_user_peer_review_items(user_id, 'group_id', 'content_id')

            self.assertEqual(result, expected_result)
            patched_get_review_items.assert_called_once_with('group_id', 'content_id')

    # pylint: disable=too-many-function-args
    @ddt.data(
        (
            1, 'content_1',
            [mri(1, 'qwe', peer=7, content_id='content_1'), mri(1, 'asd', peer=7, content_id='content_1')],
            [mri(1, 'qwe', peer=7, content_id='content_1'), mri(1, 'asd', peer=7, content_id='content_1')]),
        (
            5, 'content_2',
            [mri(5, 'qwe', peer=14, content_id='content_2'), mri(5, 'asd', peer=19, content_id='content_2')],
            [mri(5, 'qwe', peer=14, content_id='content_2'), mri(5, 'asd', peer=19, content_id='content_2')]
        ),
        (
            11, 'content_3',
            [mri(11, 'qwe', peer=3, content_id='content_2'), mri(16, 'asd', peer=4, content_id='content_3')], []
        ),
        (
            11, 'content_4',
            [mri(12, 'qwe', peer=18, content_id='content_4'), mri(11, 'question1', peer=18, content_id='content_4')],
            [mri(11, 'question1', peer=18, content_id='content_4')]
        ),
    )
    @ddt.unpack
    def test_get_workgroup_review_items(self, reviewer_id, content_id, review_items, expected_result):
        with mock.patch.object(self.project_api, 'get_workgroup_review_items_for_group') as patched_get_review_items:
            patched_get_review_items.return_value = review_items
            result = self.project_api.get_workgroup_review_items(reviewer_id, 'group_id', content_id)

            self.assertEqual(result, expected_result)
            patched_get_review_items.assert_called_once_with('group_id', content_id)

    def assert_project_data(self, project_data, expected_values):
        attrs_to_test = [
            "id", "url", "created", "modified", "course_id", "content_id", "organization", "workgroups"
        ]
        for attr in attrs_to_test:
            self.assertEqual(getattr(project_data, attr), expected_values[attr])

    def test_get_project_details(self):
        calls_and_results = {
            (PROJECTS_API, 1): CannedResponses.Projects.project1,
            (PROJECTS_API, 2): CannedResponses.Projects.project2
        }

        expected_calls = [
            call(GET, (PROJECTS_API, 1), no_trailing_slash=True),
            call(GET, (PROJECTS_API, 2), no_trailing_slash=True)
        ]

        with self._patch_send_request(calls_and_results) as patched_send_request:
            project1 = self.project_api.get_project_details(1)
            project2 = self.project_api.get_project_details(2)

            self.assertEqual(patched_send_request.mock_calls, expected_calls)

        self.assert_project_data(project1, CannedResponses.Projects.project1)
        self.assert_project_data(project2, CannedResponses.Projects.project2)

    @ddt.data(
        ('course1', 'content1'),
        ('course2', 'content2'),
    )
    @ddt.unpack
    def test_get_project_by_content_id(self, course_id, content_id):
        expected_parameters = {
            'course_id': course_id,
            'content_id': content_id
        }
        calls_and_results = {(PROJECTS_API,): [CannedResponses.Projects.project1]}

        with self._patch_send_request(calls_and_results) as patched_send_request:
            project = self.project_api.get_project_by_content_id(course_id, content_id)
            self.assert_project_data(project, CannedResponses.Projects.project1)

            patched_send_request.assert_called_once_with(GET, (PROJECTS_API,), query_params=expected_parameters)

    def test_get_project_by_content_id_fail_if_more_than_one(self):
        calls_and_results = {(PROJECTS_API,): [CannedResponses.Projects.project1, CannedResponses.Projects.project2]}
        with self._patch_send_request(calls_and_results), self.assertRaises(AssertionError):
            self.project_api.get_project_by_content_id('irrelevant', 'irrelevant')

    def test_get_project_by_content_id_return_none_if_not_found(self):
        calls_and_results = {(PROJECTS_API,): []}
        with self._patch_send_request(calls_and_results):
            project = self.project_api.get_project_by_content_id('irrelevant', 'irrelevant')
            self.assertIsNone(project)

    @ddt.data(
        (1, CannedResponses.Workgroups.workgroup1),
        (2, CannedResponses.Workgroups.workgroup2),
    )
    @ddt.unpack
    def test_get_workgroup_by_id(self, group_id, expected_result):
        calls_and_results = {
            (WORKGROUP_API, 1): CannedResponses.Workgroups.workgroup1,
            (WORKGROUP_API, 2): CannedResponses.Workgroups.workgroup2
        }

        with self._patch_send_request(calls_and_results) as patched_send_request:
            workgroup = self.project_api.get_workgroup_by_id(group_id)
            patched_send_request.assert_called_once_with(GET, (WORKGROUP_API, group_id))

        self.assertEqual(workgroup.id, expected_result['id'])
        self.assertEqual(workgroup.project, expected_result['project'])
        self.assertEqual(len(workgroup.users), len(expected_result['users']))
        self.assertEqual([user.id for user in workgroup.users], [user['id'] for user in expected_result['users']])

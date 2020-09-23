from builtins import str
import json
from unittest import TestCase

import ddt
import mock

from group_project_v2.json_requests import GET
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.api_implementation import WORKGROUP_API, PROJECTS_API, COURSES_API
from tests.utils import TestWithPatchesMixin, find_url, make_review_item as mri
import tests.unit.project_api.canned_responses as canned_responses  # pylint: disable=useless-import-alias
from six.moves.urllib.parse import urlencode


@ddt.ddt
class TestProjectApi(TestCase, TestWithPatchesMixin):
    api_server_address = 'http://localhost'
    url_parameter = {'qwe': 'rty', 'asd': 'zxc'}

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
        # pylint: disable=unused-argument
        def side_effect(method, url, data=None):
            matched_url = find_url(url, urls_and_results)
            if matched_url:
                return urls_and_results[matched_url]
            if 'default' in urls_and_results:
                return urls_and_results['default']
            if missing_callback:
                return missing_callback(url)
            raise Exception("Response not found")

        return mock.patch.object(self.project_api, '_do_send_request', mock.Mock(side_effect=side_effect))

    @ddt.data(
        (["part1", "part2"], None, False, api_server_address + "/part1/part2/", {'error': True}),
        (["part1", "part2"], None, True, api_server_address + "/part1/part2", {'success': True}),
        (["part1", 1234, "part2"], None, True, api_server_address + "/part1/1234/part2", {'error': True}),
        (["part1", "part2", 1234], None, True, api_server_address + "/part1/part2/1234", {'success': True}),
        ([api_server_address, "part1", "part2"], None, False, api_server_address + "/part1/part2/", {'success': True}),
        (["part1", "part2", "part3"], None, False, api_server_address + "/part1/part2/part3/", {'error': True}),
        (["part1"], {'qwe': 'rty'}, False, api_server_address + "/part1/?qwe=rty",
         {'success': True, 'data': [1, 2, 3]}),
        ([api_server_address, "part1"], {'qwe': 'rty'}, False, api_server_address + "/part1/?qwe=rty", {}),
        (["part1"], url_parameter, False, api_server_address + "/part1/?" + urlencode(url_parameter), {}),
        (["part1"], url_parameter, True, api_server_address + "/part1?" + urlencode(url_parameter), {}),
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
        (["part1", "part2"], None, [123], False, api_server_address + "/part1/part2/", {'error': True}),
        (["part1", "part2"], None, 'qwerty', True, api_server_address + "/part1/part2", {'success': True}),
        (
            ["part1", "part2", "part3"], None, {'data': 11}, False,
            api_server_address + "/part1/part2/part3/", {'error': True}
        ),
        (
            ["part1"], {'qwe': 'rty'}, {'var1': 1, 'var2': 2}, False,
            api_server_address + "/part1/?qwe=rty", {'success': True, 'data': [1, 2, 3]}
        ),
        (
            ["part1"], url_parameter, {'stage': 1, 'activity': 2}, False,
            api_server_address + "/part1/?" + urlencode(url_parameter), {}
        ),
        (
            ["part1"], url_parameter, {'data': None}, True,
            api_server_address + "/part1?" + urlencode(url_parameter), {}
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

            patched_delete.assert_called_once_with(self.api_server_address + '/123/456/')

    @ddt.data(
        ('user1', 'course1', 'xblock:block-1', []),
        ('user1', 'course1', 'xblock:block-1', [1, 5]),
        ('user2', 'course-2', 'xblock:html-block-1', [1, 5, 6]),
        ('user7', 'course-15', 'xblock:construction-block-743', [6, 10, 15]),
    )
    @ddt.unpack
    def test_get_workgroups_to_review(self, user_id, course_id, xblock_id, assignment_ids):
        def assignment_data_by_id(a_id):
            return {"id": a_id, 'data': 'data' + str(a_id)}

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
            (PROJECTS_API, 1): canned_responses.Projects.project1['results'][0],
            (PROJECTS_API, 2): canned_responses.Projects.project2['results'][0]
        }

        expected_calls = [
            mock.call(GET, (PROJECTS_API, 1), no_trailing_slash=True),
            mock.call(GET, (PROJECTS_API, 2), no_trailing_slash=True)
        ]

        with self._patch_send_request(calls_and_results) as patched_send_request:
            project1 = self.project_api.get_project_details(1)
            project2 = self.project_api.get_project_details(2)

            self.assertEqual(patched_send_request.mock_calls, expected_calls)

        self.assert_project_data(project1, canned_responses.Projects.project1['results'][0])
        self.assert_project_data(project2, canned_responses.Projects.project2['results'][0])

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
        calls_and_results = {(PROJECTS_API,): canned_responses.Projects.project1}

        with self._patch_send_request(calls_and_results) as patched_send_request:
            project = self.project_api.get_project_by_content_id(course_id, content_id)
            self.assert_project_data(project, canned_responses.Projects.project1['results'][0])

            patched_send_request.assert_called_once_with(GET, (PROJECTS_API,), query_params=expected_parameters)

    def test_get_project_by_content_id_fail_if_more_than_one(self):
        calls_and_results = {
            (PROJECTS_API,): canned_responses.Projects.two_projects
        }
        with self._patch_send_request(calls_and_results), \
                self.assertRaises(AssertionError):
            self.project_api.get_project_by_content_id('irrelevant', 'irrelevant')

    def test_get_project_by_content_id_return_none_if_not_found(self):
        calls_and_results = {(PROJECTS_API,): canned_responses.Projects.zero_projects}
        with self._patch_send_request(calls_and_results):
            project = self.project_api.get_project_by_content_id('irrelevant', 'irrelevant')
            self.assertIsNone(project)

    @ddt.data(
        (1, canned_responses.Workgroups.workgroup1),
        (2, canned_responses.Workgroups.workgroup2),
    )
    @ddt.unpack
    def test_get_workgroup_by_id(self, group_id, expected_result):
        calls_and_results = {
            (WORKGROUP_API, 1): canned_responses.Workgroups.workgroup1,
            (WORKGROUP_API, 2): canned_responses.Workgroups.workgroup2
        }

        with self._patch_send_request(calls_and_results) as patched_send_request:
            workgroup = self.project_api.get_workgroup_by_id(group_id)
            patched_send_request.assert_called_once_with(GET, (WORKGROUP_API, group_id))

        self.assertEqual(workgroup.id, expected_result['id'])
        self.assertEqual(workgroup.project, expected_result['project'])
        self.assertEqual(len(workgroup.users), len(expected_result['users']))
        self.assertEqual([user.id for user in workgroup.users], [user['id'] for user in expected_result['users']])

    @ddt.data(
        ('course1', 'content1'),
        ('course1', 'content2'),
        ('course2', 'content3')
    )
    @ddt.unpack
    def test_get_completions_by_content_id(self, course_id, content_id):
        def build_url(course_id, content_id):
            return self.project_api.build_url(
                (COURSES_API, course_id, 'completions'), query_params={'content_id': content_id}
            )

        urls_and_results = {
            build_url('course1', 'content1'): canned_responses.Completions.non_paged1,
            build_url('course1', 'content2'): canned_responses.Completions.non_paged2,
            build_url('course2', 'content3'): canned_responses.Completions.empty,
        }

        expected_url = build_url(course_id, content_id)
        expected_data = urls_and_results.get(expected_url)

        with self._patch_do_send_request(urls_and_results) as patched_do_send_request:
            completions = list(self.project_api.get_completions_by_content_id(course_id, content_id))
            patched_do_send_request.assert_called_once_with(GET, expected_url, None)

        self.assertEqual(len(completions), len(expected_data['results']))
        self.assertEqual([comp.id for comp in completions], [data['id'] for data in expected_data['results']])

    def test_get_completions_by_content_id_paged(self):
        def build_url(course_id, content_id, page_num=None):
            query_params = {'content_id': content_id}
            if page_num:
                query_params = {'page': page_num, 'content_id': content_id}
            return self.project_api.build_url((COURSES_API, course_id, 'completions'), query_params=query_params)

        course, content = 'course1', 'content1'

        urls_and_results = {
            build_url(course, content): canned_responses.Completions.paged_page1,
            build_url(course, content, 1): canned_responses.Completions.paged_page1,
            build_url(course, content, 2): canned_responses.Completions.paged_page2,
            build_url(course, content, 3): canned_responses.Completions.paged_page3,
        }
        all_responses = []
        pages = [
            canned_responses.Completions.paged_page1,
            canned_responses.Completions.paged_page2,
            canned_responses.Completions.paged_page3
        ]
        for page in pages:
            all_responses.extend(page['results'])

        expected_calls = [
            mock.call(GET, build_url(course, content), None),
            mock.call(GET, canned_responses.Completions.paged_page1['next'], None),
            mock.call(GET, canned_responses.Completions.paged_page2['next'], None),
        ]

        with self._patch_do_send_request(urls_and_results) as patched_do_send_request:
            completions = list(self.project_api.get_completions_by_content_id(course, content))
            self.assertEqual(patched_do_send_request.mock_calls, expected_calls)

        self.assertEqual(len(completions), len(all_responses))
        self.assertEqual([comp.id for comp in completions], [data['id'] for data in all_responses])
        self.assertEqual([comp.user_id for comp in completions], [data['user_id'] for data in all_responses])

    @ddt.data(
        ({'foo', 'bar', 'baz'}, 1234, 4321),
        ({'foo', 'bar'}, 1, 2),
        ({'foo'}, 2, 1),
        (set(), 4321, 1234),
    )
    @ddt.unpack
    def test_get_user_roles_for_course(self, roles, user_id, course_id):
        self.project_api.send_request = mock.Mock(return_value=[
            {'role': role, 'id': user_id} for role in roles
        ])
        response = self.project_api.get_user_roles_for_course(user_id, course_id)
        self.assertEqual(response, roles)
        self.project_api.send_request.assert_called_once_with(
            GET, ('api/server/courses', course_id, 'roles'), query_params={'user_id': user_id}
        )

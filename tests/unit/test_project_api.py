import json
from unittest import TestCase
import ddt
import mock
from group_project_v2.json_requests import GET
from group_project_v2.project_api import ProjectAPI, WORKGROUP_API
from tests.utils import TestWithPatchesMixin, make_review_item as mri


@ddt.ddt
class TestProjectApi(TestCase, TestWithPatchesMixin):
    api_server_address = 'http://localhost/api'

    def setUp(self):
        self.project_api = ProjectAPI(self.api_server_address, dry_run=False)

    def _patch_send_request(self, calls_and_results, misisng_callback=None):
        # pylint: disable=unused-argument
        def side_effect(method, url_parts, data=None, query_params=None, no_trailing_slash=False):
            if url_parts in calls_and_results:
                return calls_and_results[url_parts]
            if 'default' in calls_and_results:
                return calls_and_results['default']
            if misisng_callback:
                return misisng_callback(url_parts)
            return None

        return mock.patch.object(self.project_api, 'send_request', mock.Mock(side_effect=side_effect))

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
        proj_api = ProjectAPI(self.api_server_address, True)
        result = proj_api.send_request(method, ('123', '34'))
        method.assert_not_called()
        self.assertEqual(result, {})

    def test_send_delete_request_returns_none(self):
        with mock.patch('group_project_v2.project_api.DELETE') as patched_delete:
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
        ('course-1', 'content-1', 'stage-1', None),
        ('course-1', 'content-1', 'stage-1', []),
        ('course-2', 'content-2', 'stage-2', [1, 2, 3]),
        ('other_course', 'no_content', 'missing_stage', [120, 514, 997]),
    )
    @ddt.unpack
    def test_get_stage_state(self, course_id, content_id, stage, completed_users):
        if completed_users:
            completions = [{'user_id': user_id} for user_id in completed_users]
            expected_result = set(completed_users)
        else:
            completions = None
            expected_result = set()

        with mock.patch.object(self.project_api, 'get_stage_completions') as patched_get_stage_completions:
            patched_get_stage_completions.return_value = completions
            result = self.project_api.get_stage_state(course_id, content_id, stage)

            self.assertEqual(result, expected_result)
            patched_get_stage_completions.assert_called_once_with(course_id, content_id, stage)

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

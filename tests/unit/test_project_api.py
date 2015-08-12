import json
from unittest import TestCase
import ddt
import mock
from group_project_v2.project_api import ProjectAPI
from tests.utils import TestWithPatchesMixin


@ddt.ddt
class TestProjectApi(TestCase, TestWithPatchesMixin):
    api_server_address = 'http://localhost/api'

    def setUp(self):
        self.project_api = ProjectAPI(self.api_server_address, dry_run=False)

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

    #pylint: disable=too-many-arguments
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

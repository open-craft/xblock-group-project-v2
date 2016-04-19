import json
from unittest import TestCase
from xml.etree import ElementTree

import ddt
import mock
from datetime import datetime
from freezegun import freeze_time
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds
from xblock.runtime import Runtime
from xblock.validation import ValidationMessage

from group_project_v2 import messages
from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import TypedProjectAPI
from group_project_v2.project_api.dtos import WorkgroupDetails
from group_project_v2.project_navigator import ProjectNavigatorViewXBlockBase
from group_project_v2.stage import BaseGroupActivityStage
from group_project_v2.stage_components import (
    StaticContentBaseXBlock, GroupProjectSubmissionXBlock,
    GroupProjectReviewQuestionXBlock, GroupProjectTeamEvaluationDisplayXBlock, GroupProjectGradeEvaluationDisplayXBlock
)
from group_project_v2.upload_file import UploadFile
from tests.utils import TestWithPatchesMixin, make_api_error, make_review_item as mri, make_question


class StageComponentXBlockTestBase(TestCase, TestWithPatchesMixin):
    block_to_test = None

    def setUp(self):
        super(StageComponentXBlockTestBase, self).setUp()
        self.runtime_mock = mock.create_autospec(Runtime)
        self.stage_mock = mock.create_autospec(BaseGroupActivityStage)

        # pylint: disable=not-callable
        self.block = self.block_to_test(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())
        self.make_patch(self.block_to_test, 'stage', mock.PropertyMock(return_value=self.stage_mock))

    def _assert_empty_fragment(self, fragment):  # pylint: disable=no-self-use
        self.assertEqual(fragment.content, u'')
        self.assertEqual(fragment.resources, [])


class TestableStaticContentXBlock(StaticContentBaseXBlock):
    TARGET_PROJECT_NAVIGATOR_VIEW = 'some-pn-view'
    TEXT_TEMPLATE = u"Static content for {activity_name}"


@ddt.ddt
class TestStaticContentBaseXBlockMixin(StageComponentXBlockTestBase):
    block_to_test = TestableStaticContentXBlock

    def _set_up_navigator(self, activity_name='Activity 1'):
        stage = self.stage_mock

        activity = mock.create_autospec(GroupActivityXBlock)
        activity.display_name = activity_name
        stage.activity = activity

        nav = mock.Mock()
        stage.activity.project.navigator = nav
        return nav

    def test_student_view_no_path_to_navigator(self):
        self.stage_mock = None
        self._assert_empty_fragment(self.block.student_view({}))

        self.stage_mock = mock.create_autospec(BaseGroupActivityStage)
        stage = self.stage_mock
        stage.activity = None
        self._assert_empty_fragment(self.block.student_view({}))

        stage.activity = mock.Mock()
        stage.activity.project = None
        self._assert_empty_fragment(self.block.student_view({}))

        stage.activity.project = mock.Mock()
        stage.activity.project.navigator = None
        self._assert_empty_fragment(self.block.student_view({}))

    def test_student_view_no_target_block(self):
        navigator_mock = self._set_up_navigator()
        navigator_mock.get_child_of_category = mock.Mock(return_value=None)

        self._assert_empty_fragment(self.block.student_view({}))
        navigator_mock.get_child_of_category.assert_called_once_with(self.block.TARGET_PROJECT_NAVIGATOR_VIEW)

    @ddt.data(
        ({'additional': 'context'}, u"Rendered content", "activity 1"),
        ({'other': 'additional'}, u"Other content", "Activity 2"),
    )
    @ddt.unpack
    def test_student_view_normal(self, additional_context, content, activity_name):
        target_block = mock.Mock(spec=ProjectNavigatorViewXBlockBase)
        target_block.icon = "I'm icon"
        target_block.scope_ids = mock.create_autospec(spec=ScopeIds)

        navigator_mock = self._set_up_navigator(activity_name)
        navigator_mock.get_child_of_category.return_value = target_block

        with mock.patch('group_project_v2.stage_components.loader.render_template') as patched_render_template, \
                mock.patch('group_project_v2.stage_components.get_link_to_block') as patched_get_link_to_block:
            patched_render_template.return_value = content
            patched_get_link_to_block.return_value = "some link"

            expected_context = {
                'block': self.block,
                'block_link': 'some link',
                'block_text': TestableStaticContentXBlock.TEXT_TEMPLATE.format(activity_name=activity_name),
                'target_block_id': str(target_block.scope_ids.usage_id),
                'view_icon': target_block.icon
            }
            expected_context.update(additional_context)

            fragment = self.block.student_view(additional_context)
            self.assertEqual(fragment.content, content)

            patched_get_link_to_block.assert_called_once_with(target_block)
            patched_render_template.assert_called_once_with(StaticContentBaseXBlock.TEMPLATE_PATH, expected_context)


@ddt.ddt
class TestGroupProjectSubmissionXBlock(StageComponentXBlockTestBase):
    block_to_test = GroupProjectSubmissionXBlock

    group_id = 152
    user_id = "student_1"
    course_id = "a course"

    def setUp(self):
        super(TestGroupProjectSubmissionXBlock, self).setUp()
        self.project_api_mock = mock.create_autospec(TypedProjectAPI)
        self.make_patch(self.block_to_test, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        user_details = mock.Mock(user_label='Test label')
        self.block_to_test.project_api.get_user_details = mock.Mock(
            spec=TypedProjectAPI.get_user_details, return_value=user_details
        )

        self.project_api_mock.get_latest_workgroup_submissions_by_id = mock.Mock(return_value={})

        self.stage_mock.available_now = True
        self.stage_mock.activity = mock.Mock()
        self.stage_mock.activity.user_id = self.user_id
        self.stage_mock.activity.workgroup = WorkgroupDetails(id=self.group_id)
        self.stage_mock.activity.course_id = self.course_id

    @ddt.data(1, 'qwe', 'upload 1')
    def test_upload(self, upload_id):
        upload_datetime = datetime(2015, 11, 19, 22, 54, 13)  # need to be offset-naive
        self.block.upload_id = upload_id
        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = {
            upload_id: {
                "document_url": 'some_url',
                "document_filename": 'some_filename',
                "modified": upload_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "user_details": {"id": 1, "name": 'qwe'}
            }
        }

        with mock.patch('group_project_v2.stage_components.format_date') as patched_format_date:
            patched_format_date.return_value = "Aug 22"
            upload = self.block.upload

            self.project_api_mock.get_latest_workgroup_submissions_by_id.assert_called_once_with(self.group_id)

            patched_format_date.assert_called_once_with(upload_datetime)

            self.assertEqual(upload.location, 'some_url')
            self.assertEqual(upload.file_name, 'some_filename')
            self.assertEqual(upload.submission_date, 'Aug 22')
            self.assertEqual(upload.user_details, {"id": 1, "name": 'qwe'})

    def test_no_upload(self):
        self.block.upload_id = 150

        self.project_api_mock.get_latest_workgroup_submissions_by_id.return_value = {1: {}, 2: {}}
        self.assertIsNone(self.block.upload)

    def test_upload_submission_stage_is_not_available(self):
        self.stage_mock.available_now = False
        self.stage_mock.STAGE_ACTION = 'something'

        response = self.block.upload_submission(mock.Mock())
        self.assertEqual(response.status_code, 422)

    def test_upload_submission_stage_is_not_group_member(self):
        self.stage_mock.is_group_member = False
        self.stage_mock.is_admin_grader = False

        response = self.block.upload_submission(mock.Mock())
        self.assertEqual(response.status_code, 403)

    @ddt.data(
        (Exception("exception message"), 500),
        (make_api_error(418, "other message"), 418),
        (make_api_error(401, "yet another message"), 401),
    )
    @ddt.unpack
    def test_upload_submission_persist_and_submit_file_raises(self, exception, expected_code):
        upload_id = "upload_id"

        request_mock = mock.Mock()
        request_mock.params = {upload_id: mock.Mock()}
        request_mock.params[upload_id].file = "QWERTY"

        self.block.upload_id = upload_id

        with mock.patch.object(self.block, 'persist_and_submit_file') as patched_persist_and_submit_file:
            patched_persist_and_submit_file.side_effect = exception

            response = self.block.upload_submission(request_mock)
            self.assertEqual(response.status_code, expected_code)
            response_body = json.loads(response.body)
            self.assertEqual(response_body['title'], messages.FAILED_UPLOAD_TITLE)
            self.assertEqual(
                response_body['message'],
                messages.FAILED_UPLOAD_MESSAGE_TPL.format(error_goes_here=exception.message)
            )

    @ddt.data(
        ("sub1", "file.html", "new_stage_state1", False),
        ("sub2", "other_file.so", {"activity_id": 'A1', "stage_id": 'S1', 'state': 'complete'}, False),
        ("sub1", "file_ta.so", {"activity_id": 'A1', "stage_id": 'S1', 'state': 'complete'}, True),
        ("sub2", "other_file_ta.so", {"activity_id": 'A1', "stage_id": 'S1', 'state': 'complete'}, True),
    )
    @ddt.unpack
    @freeze_time("2015-08-01")
    def test_upload_submission_success_scenario(self, submission_id, file_url, stage_state, is_admin_grader):
        upload_id = "upload_id"

        self.stage_mock.is_admin_grader = is_admin_grader
        self.stage_mock.is_group_member = not is_admin_grader

        request_mock = mock.Mock()
        request_mock.params = {upload_id: mock.Mock()}
        request_mock.params[upload_id].file = "QWERTY"

        self.block.upload_id = upload_id
        self.stage_mock.get_new_stage_state_data = mock.Mock(return_value=stage_state)
        self.stage_mock.check_submissions_and_mark_complete = mock.Mock()

        expected_context = {
            "user_id": self.user_id,
            "group_id": self.group_id,
            "project_api": self.project_api_mock,
            "course_id": self.course_id
        }

        with mock.patch.object(self.block, 'persist_and_submit_file') as patched_persist_and_submit_file:
            uploaded_file_mock = mock.Mock()
            uploaded_file_mock.submission_id = submission_id
            uploaded_file_mock.file_url = file_url
            patched_persist_and_submit_file.return_value = uploaded_file_mock

            response = self.block.upload_submission(request_mock)
            self.assertEqual(response.status_code, 200)
            response_payload = json.loads(response.body)
            self.assertEqual(response_payload['title'], messages.SUCCESSFUL_UPLOAD_TITLE)
            self.assertEqual(response_payload["submissions"], {submission_id: file_url})
            self.assertEqual(response_payload["new_stage_states"], [stage_state])
            self.assertEqual(response_payload["user_label"], 'Test label')
            self.assertEqual(response_payload["submission_date"], 'Aug 01')

            self.stage_mock.check_submissions_and_mark_complete.assert_called_once_with()
            patched_persist_and_submit_file.assert_called_once_with(
                self.stage_mock.activity, expected_context, "QWERTY"
            )

    def test_persist_and_submit_file_propagates_exceptions(self):
        context_mock = mock.Mock()
        file_stream_mock = mock.Mock()

        with mock.patch('group_project_v2.stage_components.UploadFile') as upload_file_class_mock:
            upload_file_mock = mock.create_autospec(UploadFile)
            upload_file_mock.save_file = mock.Mock(side_effect=Exception("some error"))
            upload_file_mock.file = mock.Mock()
            upload_file_mock.file.name = 'file_name'
            upload_file_class_mock.return_value = upload_file_mock

            with self.assertRaises(Exception) as raises_cm:
                self.block.persist_and_submit_file(self.stage_mock.activity, context_mock, file_stream_mock)
                exception = raises_cm.exception
                expected_message = "Error storing file {} - {}".format(upload_file_mock.file.name, "some error")
                self.assertEqual(exception.message, expected_message)

            upload_file_mock.save_file.side_effect = lambda: 1
            upload_file_mock.submit = mock.Mock(side_effect=Exception("other error"))

            with self.assertRaises(Exception) as raises_cm:
                self.block.persist_and_submit_file(self.stage_mock.activity, context_mock, file_stream_mock)
                exception = raises_cm.exception
                expected_message = "Error recording file information {} - {}".format(
                    upload_file_mock.file.name, "other error"
                )
                self.assertEqual(exception.message, expected_message)

    @ddt.data(1, "upload 12", "iddqd")
    def test_persist_and_submit_file_success_path(self, upload_id):
        self.block.upload_id = upload_id
        self.stage_mock.activity.content_id = 'content_id 12'
        self.stage_mock.fire_file_upload_notification = mock.Mock()
        context_mock = mock.Mock()
        file_stream_mock = mock.Mock()

        self.runtime_mock.publish = mock.Mock()
        notification_service_mock = mock.Mock()
        self.runtime_mock.service.return_value = notification_service_mock

        with mock.patch('group_project_v2.stage_components.UploadFile') as upload_file_class_mock:
            upload_file_mock = mock.create_autospec(UploadFile)
            upload_file_mock.submission_id = '12345'
            upload_file_mock.file = mock.Mock()
            upload_file_mock.file.name = 'file_name'
            upload_file_class_mock.return_value = upload_file_mock

            result = self.block.persist_and_submit_file(self.stage_mock.activity, context_mock, file_stream_mock)
            self.assertEqual(result, upload_file_mock)
            upload_file_class_mock.assert_called_once_with(file_stream_mock, upload_id, context_mock)

            upload_file_mock.save_file.assert_called_once_with()
            upload_file_mock.submit.assert_called_once_with()

            self.runtime_mock.publish.assert_called_once_with(
                self.block,
                self.block_to_test.SUBMISSION_RECEIVED_EVENT,
                {
                    "submission_id": '12345',
                    "filename": 'file_name',
                    "content_id": 'content_id 12',
                    "group_id": self.group_id,
                    "user_id": self.user_id,
                }
            )

            self.stage_mock.fire_file_upload_notification.assert_called_with(notification_service_mock)


@ddt.ddt
class TestGroupProjectReviewQuestionXBlock(StageComponentXBlockTestBase):
    block_to_test = GroupProjectReviewQuestionXBlock

    def test_render_content_bad_content(self):
        self.block.question_content = "imparsable as XML"

        self.assertEqual(self.block.render_content(), "")

    @ddt.data(
        ("<input type='text'/>", False, False, {'answer', 'editable'}),
        ("<textarea class='initial_class'/>", False, False, {'answer', 'editable', 'initial_class'}),
        ("<input type='text'/>", True, False, {'answer', 'editable', 'side'}),
        ("<input type='text'/>", False, True, {'answer'}),
    )
    @ddt.unpack
    def test_render_content_node_content(self, question_content, single_line, closed, expected_classes):
        self.block.question_content = question_content
        self.block.single_line = single_line
        self.stage_mock.is_closed = closed

        with mock.patch('group_project_v2.stage_components.outer_html') as patched_outer_html:
            expected_response = "some rendered content"
            patched_outer_html.return_value = expected_response

            response = self.block.render_content()
            self.assertEqual(response, expected_response)

            self.assertEqual(len(patched_outer_html.call_args_list), 1)  # essentially "called once with any attributes"
            call_args, call_kwargs = patched_outer_html.call_args
            self.assertEqual(call_kwargs, {})
            self.assertEqual(len(call_args), 1)
            node_to_render = call_args[0]

            self.assertIsInstance(node_to_render, ElementTree.Element)
            self.assertEqual(node_to_render.get('id'), self.block.question_id)
            self.assertEqual(node_to_render.get('name'), self.block.question_id)
            self.assertEqual(set(node_to_render.get('class').split(' ')), expected_classes)
            self.assertEqual(node_to_render.get('disabled', None), 'disabled' if closed else None)


class CommonFeedbackDisplayStageTests(object):
    def setUp(self):
        super(CommonFeedbackDisplayStageTests, self).setUp()
        self.activity_mock = mock.create_autospec(GroupActivityXBlock)
        self.stage_mock.activity = self.activity_mock

        self.project_api_mock = mock.Mock(spec=TypedProjectAPI)
        self.make_patch(self.block_to_test, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        self.block.question_id = "q1"

    @staticmethod
    def _print_messages(validation):
        for message in validation.messages:
            print message.text

    def test_validate_no_question_id_sets_error_message(self):
        self.block.question_id = None
        try:
            validation = self.block.validate()
            self.assertEqual(len(validation.messages), 1)
            self.assertEqual(validation.messages[0].type, ValidationMessage.ERROR)
            self.assertEqual(validation.messages[0].text, self.block.NO_QUESTION_SELECTED)
        except AssertionError:
            print self._print_messages(validation)
            raise

    def test_validate_question_not_found_sets_error_message(self):
        with mock.patch.object(self.block_to_test, 'question', mock.PropertyMock(return_value=None)):
            try:
                validation = self.block.validate()
                self.assertEqual(len(validation.messages), 1)
                self.assertEqual(validation.messages[0].type, ValidationMessage.ERROR)
                self.assertEqual(validation.messages[0].text, self.block.QUESTION_NOT_FOUND)
            except AssertionError:
                print self._print_messages(validation)
                raise

    def test_has_question_passes_validation(self):
        question_mock = mock.create_autospec(GroupProjectReviewQuestionXBlock)
        with mock.patch.object(self.block_to_test, 'question', mock.PropertyMock(return_value=question_mock)):
            try:
                validation = self.block.validate()
                self.assertEqual(len(validation.messages), 0)
            except AssertionError:
                print self._print_messages(validation)
                raise

    def test_question_property_no_questions(self):
        with mock.patch.object(self.block_to_test, 'activity_questions', mock.PropertyMock(return_value=[])):
            self.assertIsNone(self.block.question)

    def test_question_property_no_matching_questions(self):
        self.block.question_id = 'q1'
        questions = [make_question('123', '123'), make_question('456', '456')]
        with mock.patch.object(self.block_to_test, 'activity_questions', mock.PropertyMock(return_value=questions)):
            self.assertIsNone(self.block.question)

    def test_question_property_one_matching_question(self):
        self.block.question_id = '456'
        questions = [make_question('123', '123'), make_question('456', '456')]
        with mock.patch.object(self.block_to_test, 'activity_questions', mock.PropertyMock(return_value=questions)):
            self.assertEqual(self.block.question, questions[1])

    def test_question_property_multiple_matching_questions(self):
        self.block.question_id = '123'
        questions = [make_question('123', '123'), make_question('123', '123')]
        with mock.patch.object(self.block_to_test, 'activity_questions', mock.PropertyMock(return_value=questions)), \
                self.assertRaises(ValueError):
            _ = self.block.question  # pylint:disable=invalid-name

    def test_question_ids_values_provider(self):
        questions = [make_question('123', 'Title 1'), make_question('456', 'Title 2'), make_question('789', 'Title 3')]
        with mock.patch.object(self.block_to_test, 'activity_questions', mock.PropertyMock(return_value=questions)):
            values = self.block.question_ids_values_provider()
            self.assertEqual(values, [
                {'display_name': u'--- Not selected ---', 'value': None},
                {"display_name": 'Title 1', "value": '123'},
                {"display_name": 'Title 2', "value": '456'},
                {"display_name": 'Title 3', "value": '789'}
            ])


@ddt.ddt
class TestGroupProjectTeamEvaluationDisplayXBlock(CommonFeedbackDisplayStageTests, StageComponentXBlockTestBase):
    block_to_test = GroupProjectTeamEvaluationDisplayXBlock

    # pylint: disable=too-many-arguments
    @ddt.data(
        (1, 2, 'content-1', 'q1', [mri(1, "q1"), mri(2, "q1")], [mri(1, "q1"), mri(2, "q1")]),
        (3, 9, 'content-2', 'q2', [mri(1, "q1"), mri(2, "q1")], []),
        (7, 15, 'content-3', 'q1', [mri(1, "q1"), mri(1, "q2")], [mri(1, "q1")]),
        (7, 15, 'content-3', 'q2', [mri(1, "q1"), mri(1, "q2")], [mri(1, "q2")]),
    )
    @ddt.unpack
    def test_get_feedback(self, user_id, group_id, content_id, question_id, feedback_items, expected_result):
        self.project_api_mock.get_user_peer_review_items = mock.Mock(return_value=feedback_items)
        self.stage_mock.activity_content_id = content_id
        self.block.question_id = question_id

        with mock.patch.object(self.block_to_test, 'user_id', mock.PropertyMock(return_value=user_id)), \
                mock.patch.object(self.block_to_test, 'group_id', mock.PropertyMock(return_value=group_id)):
            result = self.block.get_feedback()

            self.project_api_mock.get_user_peer_review_items.assert_called_once_with(
                user_id, group_id, content_id
            )
            self.assertEqual(result, expected_result)

    def test_activity_questions(self):
        self.activity_mock.team_evaluation_questions = [1, 2, 3]
        self.activity_mock.peer_review_questions = [4, 5, 6]

        self.assertEqual(self.block.activity_questions, [1, 2, 3])


@ddt.ddt
class TestGroupProjectGradeEvaluationDisplayXBlock(CommonFeedbackDisplayStageTests, StageComponentXBlockTestBase):
    block_to_test = GroupProjectGradeEvaluationDisplayXBlock

    @ddt.data(
        (2, 'content-1', 'q1', [mri(1, "q1"), mri(2, "q1")], [mri(1, "q1"), mri(2, "q1")]),
        (9, 'content-2', 'q2', [mri(1, "q1"), mri(2, "q1")], []),
        (15, 'content-3', 'q1', [mri(1, "q1"), mri(1, "q2")], [mri(1, "q1")]),
        (15, 'content-3', 'q2', [mri(1, "q1"), mri(1, "q2")], [mri(1, "q2")]),
    )
    @ddt.unpack
    def test_get_feedback(self, group_id, content_id, question_id, feedback_items, expected_result):
        self.project_api_mock.get_workgroup_review_items_for_group = mock.Mock(return_value=feedback_items)
        self.stage_mock.activity_content_id = content_id
        self.block.question_id = question_id

        with mock.patch.object(self.block_to_test, 'group_id', mock.PropertyMock(return_value=group_id)):
            result = self.block.get_feedback()

            self.project_api_mock.get_workgroup_review_items_for_group.assert_called_once_with(group_id, content_id)
            self.assertEqual(result, expected_result)

    def test_activity_questions(self):
        self.activity_mock.team_evaluation_questions = [1, 2, 3]
        self.activity_mock.peer_review_questions = [4, 5, 6]

        self.assertEqual(self.block.activity_questions, [4, 5, 6])

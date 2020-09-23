from builtins import next
from builtins import str
from datetime import datetime, timedelta
from unittest import TestCase
import ddt
import mock
from group_project_v2.notifications import (
    StageNotificationsMixin,
    NotificationMessageTypes,
    NotificationScopes,
)
from group_project_v2.project_api.dtos import WorkgroupDetails
from tests.utils import TestWithPatchesMixin, parse_datetime
from edx_notifications.data import NotificationType


def get_notification_type(message_type):
    return NotificationType(
        name=message_type,
        renderer='',
        renderer_context={}
    )


def make_workgroup(user_ids):
    return WorkgroupDetails(
        users=[
            {"id": user_id, "username": "User" + str(user_id), "email": "{0}@example.com".format(user_id)}
            for user_id in user_ids
        ])


class StageNotificationsGuineaPig(StageNotificationsMixin):
    def __init__(self, activity, location='stage-location', open_date=None):
        self.activity = activity
        self.location = location
        self.user_id = activity.user_id
        self.course_id = activity.course_id
        self.workgroup = activity.workgroup
        self.open_date = open_date


WORK_GROUP1 = make_workgroup([1, 2, 3])
WORK_GROUP2 = make_workgroup([7, 12, 54])


class BaseNotificationsTestCase(TestCase):

    @staticmethod
    def raise_exception(exception):
        raise exception

    def setUp(self):
        self.notifications_service_mock = mock.Mock()
        self.notifications_service_mock.get_notification_type = mock.Mock(side_effect=get_notification_type)
        self.notifications_service_mock.bulk_publish_notification_to_users = mock.Mock()
        self.notifications_service_mock.publish_timed_notification = mock.Mock()

    def _get_call_args(self, target, including_kwargs=False):
        self.assertTrue(target.called)
        self.assertEqual(len(target.call_args_list), 1)
        args, _kwargs = target.call_args
        if including_kwargs:
            return args, _kwargs
        return args


@ddt.ddt
class TestStageNotificationsMixin(BaseNotificationsTestCase, TestWithPatchesMixin):

    def setUp(self):
        super(TestStageNotificationsMixin, self).setUp()

    @ddt.data(
        (1, 'course1', 'stage-location', WORK_GROUP1, 'Activity1'),
        (2, 'course2', 'other-stage-location', WORK_GROUP1, 'Activity2'),
        (54, 'course3', 'yet-another-stage-location', WORK_GROUP2, 'NotAnActivity'),
    )
    @ddt.unpack
    def test_file_upload_success_scenario(self, user_id, course_id, stage_location, workgroup, name):
        activity = mock.Mock(
            user_id=user_id,
            course_id=course_id,
            location='irrelevant',
            workgroup=workgroup,
            display_name=name
        )
        block = StageNotificationsGuineaPig(activity, stage_location)

        expected_user = next(user for user in workgroup.users if user.id == user_id)
        expected_action_username = expected_user.username
        expected_user_ids = {user.id for user in workgroup.users} - {user_id}

        with mock.patch('edx_notifications.data.NotificationMessage.add_click_link_params') as patched_link_params:
            block.fire_file_upload_notification(self.notifications_service_mock)

            self.notifications_service_mock.get_notification_type.assert_called_once_with(
                NotificationMessageTypes.FILE_UPLOADED
            )

            user_ids, message = self._get_call_args(self.notifications_service_mock.bulk_publish_notification_to_users)
            self.assertEqual(set(user_ids), expected_user_ids)
            self.assertEqual(message.msg_type.name, NotificationMessageTypes.FILE_UPLOADED)
            self.assertEqual(message.namespace, str(course_id))
            self.assertEqual(message.payload['action_username'], expected_action_username)
            self.assertEqual(message.payload['activity_name'], name)

            patched_link_params.assert_called_once_with(
                {'course_id': str(course_id), 'location': str(stage_location)}
            )

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_file_upload_notification_type_raises(self, exception):
        activity = mock.Mock()
        block = StageNotificationsGuineaPig(activity)

        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.get_notification_type.side_effect = \
                lambda msg_type: self.raise_exception(exception)

            block.fire_file_upload_notification(self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_file_upload_publish_raises(self, exception):
        activity = mock.Mock(
            user_id=1,
            workgroup=WORK_GROUP1,
        )
        block = StageNotificationsGuineaPig(activity)

        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.bulk_publish_notification_to_users.side_effect = \
                lambda unused_1, unused_2: self.raise_exception(exception)

            block.fire_file_upload_notification(self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

    @ddt.data(
        (1, 'course1', 'some-location', False, '2016-02-26 04:30:48'),
        (2, 'course2', 'other-location', False, None),
        (17, 'course3', 'yet-another-location', False, None),
        (109, 'course4', 'new-location', True, str(datetime.now() + timedelta(days=3))),
    )
    @ddt.unpack
    def test_grades_posted_success_scenario(self, group_id, course_id, location, ignore_if_past_due, send_at):
        activity = mock.Mock(course_id=course_id, display_name='Activity Name')
        block = StageNotificationsGuineaPig(activity, location, open_date=parse_datetime(send_at))

        with mock.patch('edx_notifications.data.NotificationMessage.add_click_link_params') as patched_link_params:
            block.fire_grades_posted_notification(group_id, self.notifications_service_mock)

            self.notifications_service_mock.get_notification_type.assert_called_once_with(
                NotificationMessageTypes.GRADES_POSTED
            )

            args, kwargs = self._get_call_args(
                self.notifications_service_mock.publish_timed_notification,
                including_kwargs=True,
            )

            self.assertEqual(args, ())  # no positional arguments
            self.assertEqual(kwargs['scope_name'], NotificationScopes.WORKGROUP)
            self.assertEqual(kwargs['scope_context'], {'workgroup_id': group_id})
            self.assertIsNotNone(kwargs['send_at'])
            self.assertEqual(kwargs['ignore_if_past_due'], ignore_if_past_due)
            message = kwargs['msg']
            self.assertEqual(message.msg_type.name, NotificationMessageTypes.GRADES_POSTED)
            self.assertEqual(message.namespace, str(course_id))
            self.assertEqual(message.payload['activity_name'], 'Activity Name')

            patched_link_params.assert_called_once_with(
                {'course_id': str(course_id), 'location': str(block.location)}
            )

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_grades_posted_notification_type_raises(self, exception):
        activity = mock.Mock()
        block = StageNotificationsGuineaPig(activity, 'irrelevant')
        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.get_notification_type.side_effect = \
                lambda msg_type: self.raise_exception(exception)

            block.fire_grades_posted_notification('irrelevant', self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_grades_posted_publish_raises(self, exception):
        activity = mock.Mock(
            user_id=1,
            workgroup=WORK_GROUP1,
        )
        block = StageNotificationsGuineaPig(activity, 'irrelevant')
        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.publish_timed_notification.side_effect = exception
            block.fire_grades_posted_notification('irrelevant', self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

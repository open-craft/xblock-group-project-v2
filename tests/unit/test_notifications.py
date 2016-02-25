from unittest import TestCase
import ddt
import mock
from group_project_v2.notifications import (
    ActivityNotificationsMixin,
    StageNotificationsMixin,
    NotificationMessageTypes,
    NotificationScopes,
)
from group_project_v2.project_api.dtos import WorkgroupDetails
from tests.utils import TestWithPatchesMixin
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
            {"id": user_id, "username": "User"+str(user_id), "email": "{0}@example.com".format(user_id)}
            for user_id in user_ids
        ])


class ActivityNotificationsGuineaPig(ActivityNotificationsMixin):
    def __init__(self, user_id, course_id, location, workgroup, display_name):
        self.user_id = user_id
        self.course_id = course_id
        self.location = location
        self.workgroup = workgroup
        self.display_name = display_name


class StageNotificationsGuineaPig(StageNotificationsMixin):
    def __init__(self, activity, location='stage-location'):
        self.activity = activity
        self.location = location
        self.user_id = activity.user_id
        self.course_id = activity.course_id
        self.workgroup = activity.workgroup


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
        self.notifications_service_mock.bulk_publish_notification_to_scope = mock.Mock()

    def _get_call_args(self, target):
        self.assertTrue(target.called)
        self.assertEqual(len(target.call_args_list), 1)
        args, _kwargs = target.call_args
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
        activity = ActivityNotificationsGuineaPig(user_id, course_id, 'irrelevant', workgroup, name)
        block = StageNotificationsGuineaPig(activity, stage_location)

        expected_user = next(user for user in workgroup.users if user.id == user_id)
        expected_action_username = expected_user.username
        expected_user_ids = set([user.id for user in workgroup.users]) - {user_id}

        with mock.patch('edx_notifications.data.NotificationMessage.add_click_link_params') as patched_link_params:
            block.fire_file_upload_notification(self.notifications_service_mock)

            self.notifications_service_mock.get_notification_type.assert_called_once_with(
                NotificationMessageTypes.FILE_UPLOADED
            )

            user_ids, message = self._get_call_args(self.notifications_service_mock.bulk_publish_notification_to_users)
            self.assertEqual(set(user_ids), expected_user_ids)
            self.assertEqual(message.msg_type.name, NotificationMessageTypes.FILE_UPLOADED)
            self.assertEqual(message.namespace, unicode(course_id))
            self.assertEqual(message.payload['action_username'], expected_action_username)
            self.assertEqual(message.payload['activity_name'], name)

            patched_link_params.assert_called_once_with(
                {'course_id': unicode(course_id), 'location': unicode(stage_location)}
            )

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_file_upload_notification_type_raises(self, exception):
        activity = ActivityNotificationsGuineaPig('irrelevant', 'irrelevant', 'irrelevant', 'irrelevant', 'irrelevant')
        block = StageNotificationsGuineaPig(activity)

        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.get_notification_type.side_effect = \
                lambda msg_type: self.raise_exception(exception)

            block.fire_file_upload_notification(self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_file_upload_publish_raises(self, exception):
        activity = ActivityNotificationsGuineaPig(1, 'irrelevant', 'irrelevant', WORK_GROUP1, 'irrelevant')
        block = StageNotificationsGuineaPig(activity)

        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.bulk_publish_notification_to_users.side_effect = \
                lambda unused_1, unused_2: self.raise_exception(exception)

            block.fire_file_upload_notification(self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)


@ddt.ddt
class TestActivityNotificationsMixin(TestStageNotificationsMixin, TestWithPatchesMixin):

    def setUp(self):
        super(TestActivityNotificationsMixin, self).setUp()

    @ddt.data(
        (1, 'course1', 'some-location', 'Activity1'),
        (2, 'course2', 'other-location', 'Activity2'),
        (17, 'course3', 'yet-another-location', 'NotAnActivity'),
    )
    @ddt.unpack
    def test_grades_posted_success_scenario(self, group_id, course_id, location, name):
        block = ActivityNotificationsGuineaPig('irrelevant', course_id, location, 'irrelevant', name)

        with mock.patch('edx_notifications.data.NotificationMessage.add_click_link_params') as patched_link_params:
            block.fire_grades_posted_notification(group_id, self.notifications_service_mock)

            self.notifications_service_mock.get_notification_type.assert_called_once_with(
                NotificationMessageTypes.GRADES_POSTED
            )

            scope, scope_args, message = self._get_call_args(
                self.notifications_service_mock.bulk_publish_notification_to_scope
            )

            self.assertEqual(scope, NotificationScopes.WORKGROUP)
            self.assertEqual(scope_args, {'workgroup_id': group_id})

            self.assertEqual(message.msg_type.name, NotificationMessageTypes.GRADES_POSTED)
            self.assertEqual(message.namespace, unicode(course_id))
            self.assertEqual(message.payload['activity_name'], name)

            patched_link_params.assert_called_once_with(
                {'course_id': unicode(course_id), 'location': unicode(location)}
            )

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_grades_posted_notification_type_raises(self, exception):
        block = ActivityNotificationsGuineaPig('irrelevant', 'irrelevant', 'irrelevant', 'irrelevant', 'irrelevant')
        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.get_notification_type.side_effect = \
                lambda msg_type: self.raise_exception(exception)

            block.fire_grades_posted_notification('irrelevant', self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

    @ddt.data(ValueError("test"), TypeError("QWE"), AttributeError("OMG"), Exception("Very Generic"))
    def test_grades_posted_publish_raises(self, exception):
        block = ActivityNotificationsGuineaPig(1, 'irrelevant', 'irrelevant', WORK_GROUP1, 'irrelevant')
        with mock.patch('logging.Logger.exception') as patched_exception_logger:
            self.notifications_service_mock.bulk_publish_notification_to_scope.side_effect = \
                lambda unused_1, unused_2, unused_3: self.raise_exception(exception)

            block.fire_grades_posted_notification('irrelevant', self.notifications_service_mock)
            patched_exception_logger.assert_called_once_with(exception)

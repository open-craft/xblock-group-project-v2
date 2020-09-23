from builtins import str
from builtins import object
import logging
from datetime import datetime, timedelta
import pytz

from group_project_v2.utils import log_and_suppress_exceptions

try:
    # Python 2: "unicode" is built-in
    unicode  # pylint: disable=I0011,C0103
except NameError:
    unicode = str  # pylint: disable=I0011,C0103

try:
    from edx_notifications.data import NotificationMessage  # pylint: disable=import-error
except ImportError:
    # Notifications is an optional runtime configuration, so it may not be available for import
    pass


log = logging.getLogger(__name__)


class NotificationMessageTypes(object):
    MESSAGE_TYPE_PREFIX = u'open-edx.xblock.group-project-v2.'
    STAGE_OPEN = MESSAGE_TYPE_PREFIX + u'stage-open'
    STAGE_DUE = MESSAGE_TYPE_PREFIX + u'stage-due'
    FILE_UPLOADED = MESSAGE_TYPE_PREFIX + u'file-uploaded'
    GRADES_POSTED = MESSAGE_TYPE_PREFIX + u'grades-posted'


class NotificationTimers(object):
    OPEN = 'open'
    DUE = 'due'
    GRADE = 'grade'
    COMING_DUE = 'coming-due'


class NotificationScopes(object):
    WORKGROUP = 'group_project_workgroup'
    PARTICIPANTS = 'group_project_participants'


def add_click_link_params(msg, course_id, location):
    """
    Adds in all the context parameters we'll need to generate a URL back to the website that will
    present the new course announcement.

    IMPORTANT: This can be changed to msg.add_click_link() if we have a particular URL that we wish to use.
    In the initial use case, we need to make the link point to a different front end website so we need to
    resolve these links at dispatch time
    """
    msg.add_click_link_params({'course_id': unicode(course_id), 'location': unicode(location)})


class StageNotificationsMixin(object):
    def _get_stage_timer_name(self, timer_name_suffix):
        return '{location}-{timer_name_suffix}'.format(
            location=unicode(self.location),
            timer_name_suffix=timer_name_suffix
        )

    # pylint: disable=too-many-arguments
    def _set_activity_timed_notification(self, course_id, msg_type, event_date, send_at_date,
                                         services, timer_name_suffix):

        notifications_service = services.get('notifications')

        activity_date_tz = event_date.replace(tzinfo=pytz.UTC)
        send_at_date_tz = send_at_date.replace(tzinfo=pytz.UTC)

        msg = NotificationMessage(
            msg_type=notifications_service.get_notification_type(msg_type),
            namespace=unicode(course_id),
            payload={
                '_schema_version': 1,
                'activity_name': self.activity.display_name,
                'stage': self.display_name,
                'due_date': activity_date_tz.strftime('%-m/%-d/%-y'),
            }
        )

        add_click_link_params(msg, course_id, self.location)

        notifications_service.publish_timed_notification(
            msg=msg,
            send_at=send_at_date_tz,
            # send to all students participating in this project
            scope_name=NotificationScopes.PARTICIPANTS,
            scope_context={
                'course_id': unicode(course_id),
                'content_id': unicode(self.activity.project.location),
            },
            timer_name=self._get_stage_timer_name(timer_name_suffix),
            ignore_if_past_due=True  # don't send if we're already late!
        )

    @log_and_suppress_exceptions
    def on_studio_published(self, course_id, services):
        """
        A hook into when this xblock is published in Studio. When we are published we should
        register a Notification to be send on key dates
        """
        # pylint: disable=logging-format-interpolation
        log.info('{}.on_published() on location = {}'.format(self.__class__.__name__, self.location))

        notifications_service = services.get('notifications')
        if notifications_service:
            if self.open_date:
                self._set_activity_timed_notification(
                    course_id,
                    NotificationMessageTypes.STAGE_OPEN,
                    datetime.combine(self.open_date, datetime.min.time()),
                    datetime.combine(self.open_date, datetime.min.time()),
                    services,
                    NotificationTimers.OPEN
                )

            if self.close_date:
                self._set_activity_timed_notification(
                    course_id,
                    NotificationMessageTypes.STAGE_DUE,
                    datetime.combine(self.close_date, datetime.min.time()),
                    datetime.combine(self.close_date, datetime.min.time()),
                    services,
                    NotificationTimers.DUE
                )

                # send a notice 3 days prior to closing stage
                self._set_activity_timed_notification(
                    course_id,
                    NotificationMessageTypes.STAGE_DUE,
                    datetime.combine(self.close_date, datetime.min.time()),
                    datetime.combine(self.close_date, datetime.min.time()) - timedelta(days=3),
                    services,
                    NotificationTimers.COMING_DUE
                )

    @log_and_suppress_exceptions
    def on_before_studio_delete(self, _course_id, services):
        """
        A hook into when this xblock is deleted in Studio, for xblocks to do any lifecycle
        management
        :param CourseLocator _course_id: Course ID
        :param dict[str, object] services: runtime services
        """
        # pylint: disable=logging-format-interpolation
        log.info('{}.on_before_delete() on location = {}'.format(self.__class__.__name__, self.location))
        notifications_service = services.get('notifications')
        if notifications_service:
            # If stage is being deleted, then it should remove any NotificationTimers that
            # may have been registered before
            for timer_suffix in (NotificationTimers.OPEN, NotificationTimers.DUE, NotificationTimers.COMING_DUE):
                notifications_service.cancel_timed_notification(self._get_stage_timer_name(timer_suffix))

    @log_and_suppress_exceptions
    def fire_file_upload_notification(self, notifications_service):
        # pylint: disable=logging-format-interpolation
        log.info('{}.fire_file_upload_notification on location = {}'.format(self.__class__.__name__, self.location))
        # this NotificationType is registered in the list of default Open edX Notifications
        msg_type = notifications_service.get_notification_type(NotificationMessageTypes.FILE_UPLOADED)

        workgroup_user_ids = []
        uploader_username = ''
        for user in self.workgroup.users:
            # don't send to ourselves
            if user.id != self.user_id:
                workgroup_user_ids.append(user.id)
            else:
                uploader_username = user.username

        msg = NotificationMessage(
            msg_type=msg_type,
            namespace=unicode(self.course_id),
            payload={
                '_schema_version': 1,
                'action_username': uploader_username,
                'activity_name': self.activity.display_name,
            }
        )
        location = unicode(self.location) if self.location else ''
        add_click_link_params(msg, unicode(self.course_id), location)

        # NOTE: We're not using Celery here since we are expecting that we
        # will have only a very small handful of workgroup users
        notifications_service.bulk_publish_notification_to_users(workgroup_user_ids, msg)

    @log_and_suppress_exceptions
    def fire_grades_posted_notification(self, group_id, notifications_service):
        # pylint: disable=logging-format-interpolation
        log.info(
            '{}.fire_grades_posted_notification on location = {} and group id = {}'.format(
                self.__class__.__name__, self.location,
                group_id,
            )
        )

        msg_type = notifications_service.get_notification_type(NotificationMessageTypes.GRADES_POSTED)
        msg = NotificationMessage(
            msg_type=msg_type,
            namespace=unicode(self.course_id),
            payload={
                '_schema_version': 1,
                'activity_name': self.activity.display_name,
            }
        )
        location = unicode(self.location) if self.location else ''
        add_click_link_params(msg, unicode(self.course_id), location)

        send_at_date = self.open_date.replace(tzinfo=pytz.UTC) if self.open_date else None
        ignore_if_past_due = True
        current_datetime = datetime.now().replace(tzinfo=pytz.UTC)
        if not send_at_date or current_datetime > send_at_date:
            send_at_date = current_datetime
            ignore_if_past_due = False

        notifications_service.publish_timed_notification(
            msg=msg,
            send_at=send_at_date,
            scope_name=NotificationScopes.WORKGROUP,
            scope_context={
                'workgroup_id': group_id,
            },
            timer_name=self._get_stage_timer_name(NotificationTimers.GRADE),
            ignore_if_past_due=ignore_if_past_due
        )

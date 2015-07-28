import logging
import pytz

from datetime import datetime, timedelta
from group_project_v2.utils import log_and_suppress_exceptions

try:
    from edx_notifications.data import NotificationMessage  # pylint: disable=import-error
except ImportError:
    # Notifications is an optional runtime configuration, so it may not be available for import
    pass


log = logging.getLogger(__name__)


def add_click_link_params(msg, course_id, location):
    """
    Adds in all the context parameters we'll need to generate a URL back to the website that will
    present the new course announcement.

    IMPORTANT: This can be changed to msg.add_click_link() if we have a particular URL that we wish to use.
    In the initial use case, we need to make the link point to a different front end website so we need to
    resolve these links at dispatch time
    """
    msg.add_click_link_params({'course_id': unicode(course_id), 'activity_location': unicode(location)})


class StageNotificationsMixin(object):
    def _get_stage_timer_name(self, timer_name_suffix):
        return '{location}-{timer_name_suffix}'.format(
            location=unicode(self.location),
            timer_name_suffix=timer_name_suffix
        )

    # pylint: disable=too-many-arguments
    def _set_activity_timed_notification(self, course_id, msg_type, event_date, send_at_date,
                                         services, timer_name_suffix):

        stage_name = self.display_name
        notifications_service = services.get('notifications')

        activity_date_tz = event_date.replace(tzinfo=pytz.UTC)
        send_at_date_tz = send_at_date.replace(tzinfo=pytz.UTC)

        msg = NotificationMessage(
            msg_type=notifications_service.get_notification_type(msg_type),
            namespace=unicode(course_id),
            payload={
                '_schema_version': 1,
                'activity_name': self.activity.display_name,
                'stage': stage_name,
                'due_date': activity_date_tz.strftime('%-m/%-d/%-y'),
            }
        )

        add_click_link_params(msg, course_id, self.activity.location)

        notifications_service.publish_timed_notification(
            msg=msg,
            send_at=send_at_date_tz,
            # send to all students participating in this project
            scope_name='group_project_participants',
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
        log.info('{}.on_published() on location = {}'.format(self.__class__.__name__, self.location))

        notifications_service = services.get('notifications')
        if notifications_service:
            if self.open_date:
                self._set_activity_timed_notification(
                    course_id,
                    u'open-edx.xblock.group-project.stage-open',
                    datetime.combine(self.open_date, datetime.min.time()),
                    datetime.combine(self.open_date, datetime.min.time()),
                    services,
                    'open'
                )

            if self.close_date:
                self._set_activity_timed_notification(
                    course_id,
                    u'open-edx.xblock.group-project.stage-due',
                    datetime.combine(self.close_date, datetime.min.time()),
                    datetime.combine(self.close_date, datetime.min.time()),
                    services,
                    'due'
                )

                # send a notice 3 days prior to closing stage
                self._set_activity_timed_notification(
                    course_id,
                    u'open-edx.xblock.group-project.stage-due',
                    datetime.combine(self.close_date, datetime.min.time()),
                    datetime.combine(self.close_date, datetime.min.time()) - timedelta(days=3),
                    services,
                    'coming-due'
                )

    @log_and_suppress_exceptions
    def on_before_studio_delete(self, course_id, services):  # pylint: disable=unused-argument
        """
        A hook into when this xblock is deleted in Studio, for xblocks to do any lifecycle
        management
        """
        log.info('{}.on_before_delete() on location = {}'.format(self.__class__.__name__, self.location))

        notifications_service = services.get('notifications')
        if notifications_service:
            # If we are being delete, then we should remove any NotificationTimers that
            # may have been registered before
            notifications_service.cancel_timed_notification(self._get_stage_timer_name('open'))

            notifications_service.cancel_timed_notification(self._get_stage_timer_name('due'))

            notifications_service.cancel_timed_notification(self._get_stage_timer_name('coming-due'))


class ActivityNotificationsMixin(object):
    # While we *should* send notification, if there is some error here, we don't want to blow the whole thing up.
    @log_and_suppress_exceptions
    def fire_file_upload_notification(self, notifications_service):
        # this NotificationType is registered in the list of default Open edX Notifications
        msg_type = notifications_service.get_notification_type('open-edx.xblock.group-project.file-uploaded')

        workgroup_user_ids = []
        uploader_username = ''
        for user in self.workgroup['users']:
            # don't send to ourselves
            if user['id'] != self.user_id:
                workgroup_user_ids.append(user['id'])
            else:
                uploader_username = user['username']

        msg = NotificationMessage(
            msg_type=msg_type,
            namespace=unicode(self.course_id),
            payload={
                '_schema_version': 1,
                'action_username': uploader_username,
                'activity_name': self.display_name,
            }
        )
        location = unicode(self.location) if self.location else ''
        add_click_link_params(msg, unicode(self.course_id), location)

        # NOTE: We're not using Celery here since we are expecting that we
        # will have only a very small handful of workgroup users
        notifications_service.bulk_publish_notification_to_users(workgroup_user_ids, msg)

    # While we *should* send notification, if there is some error here, we don't want to blow the whole thing up.
    @log_and_suppress_exceptions
    def fire_grades_posted_notification(self, group_id, notifications_service):
        # this NotificationType is registered in the list of default Open edX Notifications
        msg_type = notifications_service.get_notification_type('open-edx.xblock.group-project.grades-posted')
        msg = NotificationMessage(
            msg_type=msg_type,
            namespace=unicode(self.course_id),
            payload={
                '_schema_version': 1,
                'activity_name': self.display_name,
            }
        )
        location = unicode(self.location) if self.location else ''
        self._add_click_link_params(msg, unicode(self.course_id), location)

        # Bulk publish to the 'group_project_workgroup' user scope
        notifications_service.bulk_publish_notification_to_scope(
            'group_project_workgroup',
            {'workgroup_id': group_id},
            msg
        )

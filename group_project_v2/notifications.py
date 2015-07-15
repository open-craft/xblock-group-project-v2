import logging
import pytz

from datetime import datetime, timedelta

try:
    from edx_notifications.data import NotificationMessage  # pylint: disable=import-error
except ImportError:
    # Notifications is an optional runtime configuration, so it may not be available for import
    pass


log = logging.getLogger(__name__)


class BaseNotificationsMixin(object):
    def _get_stage_timer_name(self, timer_name_suffix):
        return '{location}-{timer_name_suffix}'.format(
            location=self.location,
            timer_name_suffix=timer_name_suffix
        )

    def get_courseware_info(self, courseware_parent_info_service):
        activity_name = self.display_name
        activity_location = None
        stage_name = self.display_name
        stage_location = None
        project_name = None
        project_location = None

        try:
            if courseware_parent_info_service:
                # First get Unit (first parent)
                stage_info = courseware_parent_info_service.get_parent_info(self.location)
                stage_location = stage_info['location']
                stage_name = stage_info['display_name']

                # Then get Sequence (second parent)
                activity_courseware_info = courseware_parent_info_service.get_parent_info(
                    stage_location
                )
                activity_name = activity_courseware_info['display_name']
                activity_location = activity_courseware_info['location']

                project_courseware_info = courseware_parent_info_service.get_parent_info(
                    activity_location
                )
                project_name = project_courseware_info['display_name']
                project_location = project_courseware_info['location']

        except Exception, ex:  # pylint: disable=broad-except
            # Can't look this up then log and just use the default
            # which is our display_name
            log.exception(ex)

        return {
            'stage_name': stage_name,
            'stage_location': stage_location,
            'activity_name': activity_name,
            'activity_location': activity_location,
            'project_name': project_name,
            'project_location': project_location,
        }


class StageNotificationsMixin(BaseNotificationsMixin):
    def _set_activity_timed_notification(self, course_id, msg_type, activity_date, send_at_date,
                                         services, timer_name_suffix):

        stage_name = self.display_name
        notifications_service = services.get('notifications')
        courseware_parent_info = services.get('courseware_parent_info')

        courseware_info = self.get_courseware_info(courseware_parent_info)

        activity_name = courseware_info['activity_name']
        activity_location = courseware_info['activity_location']

        project_location = courseware_info['project_location']

        activity_date_tz = activity_date.replace(tzinfo=pytz.UTC)
        send_at_date_tz = send_at_date.replace(tzinfo=pytz.UTC)

        msg = NotificationMessage(
            msg_type=notifications_service.get_notification_type(msg_type),
            namespace=unicode(course_id),
            payload={
                '_schema_version': 1,
                'activity_name': activity_name,
                'stage': stage_name,
                'due_date': activity_date_tz.strftime('%-m/%-d/%-y'),
            }
        )

        #
        # add in all the context parameters we'll need to
        # generate a URL back to the website that will
        # present the new course announcement
        #
        # IMPORTANT: This can be changed to msg.add_click_link() if we
        # have a particular URL that we wish to use. In the initial use case,
        # we need to make the link point to a different front end website
        # so we need to resolve these links at dispatch time
        #
        msg.add_click_link_params({
            'course_id': unicode(course_id),
            'activity_location': unicode(activity_location),
        })

        notifications_service.publish_timed_notification(
            msg=msg,
            send_at=send_at_date_tz,
            # send to all students participating in this project
            scope_name='group_project_participants',
            scope_context={
                'course_id': unicode(course_id),
                'content_id': unicode(project_location),
            },
            timer_name=self._get_stage_timer_name(timer_name_suffix),
            ignore_if_past_due=True  # don't send if we're already late!
        )

    def on_studio_published(self, course_id, services):
        """
        A hook into when this xblock is published in Studio. When we are published we should
        register a Notification to be send on key dates
        """
        try:
            log.info('{}.on_published() on location = {}'.format(self.__class__.__name__, self.location))

            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # set (or update) Notification timed message based on
                # the current key dates

                # if the stage has a opening date, then send a msg then
                if self.open_date:
                    self._set_activity_timed_notification(
                        course_id,
                        u'open-edx.xblock.group-project.stage-open',
                        datetime.combine(self.open_date, datetime.min.time()),
                        datetime.combine(self.open_date, datetime.min.time()),
                        services,
                        'open'
                    )

                # if the stage has a close date, then send a msg then
                if self.close_date:
                    self._set_activity_timed_notification(
                        course_id,
                        u'open-edx.xblock.group-project.stage-due',
                        datetime.combine(self.close_date, datetime.min.time()),
                        datetime.combine(self.close_date, datetime.min.time()),
                        services,
                        'due'
                    )

                    # and also send a notice 3 days earlier
                    self._set_activity_timed_notification(
                        course_id,
                        u'open-edx.xblock.group-project.stage-due',
                        datetime.combine(self.close_date, datetime.min.time()),
                        datetime.combine(self.close_date, datetime.min.time()) - timedelta(days=3),
                        services,
                        'coming-due'
                    )

        except Exception, ex:  # pylint: disable=broad-except
            log.exception(ex)

    def on_before_studio_delete(self, course_id, services):  # pylint: disable=unused-argument
        """
        A hook into when this xblock is deleted in Studio, for xblocks to do any lifecycle
        management
        """
        log.info('GroupActivityXBlock.on_before_delete() on location = {}'.format(self.location))

        try:
            # see if we are running in an environment which has Notifications enabled
            notifications_service = services.get('notifications')
            if notifications_service:
                # If we are being delete, then we should remove any NotificationTimers that
                # may have been registered before
                notifications_service.cancel_timed_notification(self._get_stage_timer_name('open'))

                notifications_service.cancel_timed_notification(self._get_stage_timer_name('due'))

                notifications_service.cancel_timed_notification(self._get_stage_timer_name('coming-due'))

        except Exception, ex:  # pylint: disable=broad-except
            log.exception(ex)


class ActivityNotificationsMixin(BaseNotificationsMixin):

    # TODO: this fire_* methods are mostly identical - might make sense to refactor into single method
    def fire_file_upload_notification(self, notifications_service):
        try:
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

            # get the activity name which is simply our hosting
            # Sequence's Display Name, so call out to a new xBlock
            # runtime Service

            courseware_info = self.get_courseware_info(self.runtime.service(self, 'courseware_parent_info'))

            activity_name = courseware_info['activity_name']
            activity_location = courseware_info['activity_location']

            msg = NotificationMessage(
                msg_type=msg_type,
                namespace=unicode(self.course_id),
                payload={
                    '_schema_version': 1,
                    'action_username': uploader_username,
                    'activity_name': activity_name,
                }
            )

            #
            # add in all the context parameters we'll need to
            # generate a URL back to the website that will
            # present the new course announcement
            #
            # IMPORTANT: This can be changed to msg.add_click_link() if we
            # have a particular URL that we wish to use. In the initial use case,
            # we need to make the link point to a different front end website
            # so we need to resolve these links at dispatch time
            #
            msg.add_click_link_params({
                'course_id': unicode(self.course_id),
                'activity_location': unicode(activity_location) if activity_location else '',
            })

            # NOTE: We're not using Celery here since we are expectating that we
            # will have only a very small handful of workgroup users
            notifications_service.bulk_publish_notification_to_users(
                workgroup_user_ids,
                msg
            )
        except Exception, ex:  # pylint: disable=broad-except
            # While we *should* send notification, if there is some
            # error here, we don't want to blow the whole thing up.
            # So log it and continue....
            log.exception(ex)

    def fire_grades_posted_notification(self, group_id, notifications_service):
        try:
            # this NotificationType is registered in the list of default Open edX Notifications
            msg_type = notifications_service.get_notification_type('open-edx.xblock.group-project.grades-posted')

            # get the activity name which is simply our hosting
            # Sequence's Display Name, so call out to a new xBlock
            # runtime Service
            courseware_info = self.get_courseware_info(self.runtime.service(self, 'courseware_parent_info'))
            activity_name = courseware_info['activity_name']
            activity_location = courseware_info['activity_location']

            msg = NotificationMessage(
                msg_type=msg_type,
                namespace=unicode(self.course_id),
                payload={
                    '_schema_version': 1,
                    'activity_name': activity_name,
                }
            )

            #
            # add in all the context parameters we'll need to
            # generate a URL back to the website that will
            # present the new course announcement
            #
            # IMPORTANT: This can be changed to msg.add_click_link() if we
            # have a particular URL that we wish to use. In the initial use case,
            # we need to make the link point to a different front end website
            # so we need to resolve these links at dispatch time
            #
            msg.add_click_link_params({
                'course_id': unicode(self.course_id),
                'activity_location': unicode(activity_location) if activity_location else '',
            })

            # Bulk publish to the 'group_project_workgroup' user scope
            notifications_service.bulk_publish_notification_to_scope(
                'group_project_workgroup',
                {
                    # I think self.workgroup['id'] is a string version of an integer
                    'workgroup_id': group_id,
                },
                msg
            )
        except Exception, ex:  # pylint: disable=broad-except
            # While we *should* send notification, if there is some
            # error here, we don't want to blow the whole thing up.
            # So log it and continue....
            log.exception(ex)

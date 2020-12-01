/* exported GroupProjectCommon */
// Set up gettext in case it isn't available in the client runtime:
if (typeof group_project_v2_gettext === "undefined") {
    window.group_project_v2_gettext = function gettext_stub(string) {
        'use strict';
        return string;
    };
}
if (typeof window.GroupProjectV2XBlockI18N !== "undefined"){
  var group_project_v2_gettext = window.GroupProjectV2XBlockI18N.gettext; // jshint ignore:line
}

var GroupProjectEvents = {
    ProjectNavigator: {
        activate_view: 'group_project_v2.project_navigator.activate_view',
        switch_view: 'group_project_v2.project_navigator.switch_view',
        stage_status_update: 'group_project_v2.project_navigator.stage_status_update'
    },
    Discussion: {
        show_discussion: 'group_project_v2.discussion.show',
        hide_discussion: 'group_project_v2.discussion.hide'
    },
    Submission: {
        upload_started: 'group_project_v2.submission.upload_started',
        upload_failed: 'group_project_v2.submission.upload_failed',
        upload_complete: 'group_project_v2.submission.upload_complete'
    },
    Review: {
        refresh_status: "group_project_v2.review.refresh_status"
    },
    Messages: {
        show_message: 'group_project_v2.messages.show'
    }
};

var GroupProjectCommon = {
    get_root_element: function(element) {
        'use strict';
        return $(element).parents(".group-project-xblock-wrapper");
    },
    gettext: group_project_v2_gettext,
    ProjectNavigator: {
        events: GroupProjectEvents.ProjectNavigator
    },
    Discussion: {
        events: GroupProjectEvents.Discussion,
        show_discussion: function() {
            'use strict';
            $(document).trigger(GroupProjectEvents.Discussion.show_discussion);
        },
        hide_discussion: function() {
            'use strict';
            $(document).trigger(GroupProjectEvents.Discussion.hide_discussion);
        }
    },
    Submission: {
        events: GroupProjectEvents.Submission
    },
    Review: {
        events: GroupProjectEvents.Review,
        messages: {
            SELECT_PEER_TO_REVIEW: group_project_v2_gettext('Please select Teammate to review'),
            SELECT_GROUP_TO_REVIEW: group_project_v2_gettext('Please select Group to review'),

            THANKS_FOR_FEEDBACK: group_project_v2_gettext('Thanks for your feedback!'),
            ERROR_LOADING_FEEDBACK: group_project_v2_gettext('We encountered an error loading your feedback.'),
            ERROR_SAVING_FEEDBACK: group_project_v2_gettext('We encountered an error saving your feedback.'),
            ERROR_LOADING_SUBMISSIONS: group_project_v2_gettext('We encountered an error.')
        }
    },
    CompletionStage: {
        messages: {
            MARKED_AS_COMPLETE: group_project_v2_gettext('This task has been marked as complete.'),
            ERROR_SAVING_PROGRESS: group_project_v2_gettext('We encountered an error saving your progress.')
        }
    },
    Messages: {
        events: GroupProjectEvents.Messages,
        show_message: function(message, title, title_css_class) {
            'use strict';
            $(document).trigger(
                GroupProjectEvents.Messages.show_message,
                {message: message, title: title, title_css_class: title_css_class}
            );
        }
    }
};

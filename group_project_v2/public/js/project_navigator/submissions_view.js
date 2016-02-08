/* global GroupProjectCommon */
/* exported GroupProjectNavigatorSubmissionsView */
function GroupProjectNavigatorSubmissionsView(runtime, element) {
    "use strict";
    var $action_buttons = $(".action_buttons", element);

    var running_uploads = [];

    function handle_upload_end(e, uploadXHR) {
        var index = $.inArray(uploadXHR, running_uploads);
        if (index > -1) {
            running_uploads.splice(index, 1);
        }

        if (running_uploads.length === 0) {
            $action_buttons.css('visibility', 'hidden');
        }
    }

    $(document).on(GroupProjectCommon.Submission.events.upload_started, function(e, uploadXHR){
        running_uploads.push(uploadXHR);
        $action_buttons.css('visibility', 'visible');
    });

    $(document).on(GroupProjectCommon.Submission.events.upload_failed, handle_upload_end);
    $(document).on(GroupProjectCommon.Submission.events.upload_complete, handle_upload_end);

    $('.cancel_upload', element).on('click', function () {
        for (var i=0; i<running_uploads.length; i++) {
            var uploadXHR = running_uploads[i];
            uploadXHR.abort();
        }
        running_uploads = [];
        $action_buttons.css('visibility', 'hidden');
    });
}

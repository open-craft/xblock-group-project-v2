function GroupProjectNavigatorSubmissionsView(runtime, element) {
    "use strict";
    var upload_started_event = 'group_project_v2.submission.upload_started';
    var upload_failed_event = 'group_project_v2.submission.upload_failed';
    var upload_complete_event = 'group_project_v2.submission.upload_complete';

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

    $(document).on(upload_started_event, function(e, uploadXHR){
        running_uploads.push(uploadXHR);
        $action_buttons.css('visibility', 'visible');
    });

    $(document).on(upload_failed_event, handle_upload_end);
    $(document).on(upload_complete_event, handle_upload_end);

    $('.cancel_upload', element).on('click', function () {
        for (var i=0; i<running_uploads.length; i++) {
            var uploadXHR = running_uploads[i];
            uploadXHR.abort();
        }
        running_uploads = [];
        $action_buttons.css('visibility', 'hidden');
    });
}

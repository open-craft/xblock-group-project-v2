/* global GroupProjectCommon */
/* exported GroupProjectNavigatorSubmissionsView */
function GroupProjectNavigatorSubmissionsView(runtime, element) {
    "use strict";
    var $cancel_button = $(".cancel_upload", element);

    var running_uploads = [];

    function handle_upload_end(e, uploadXHR) {
        var index = $.inArray(uploadXHR, running_uploads);
        if (index > -1) {
            running_uploads.splice(index, 1);
        }

        if (running_uploads.length === 0) {
            $cancel_button.css('visibility', 'hidden');
        }
    }

    $(document).on(GroupProjectCommon.Submission.events.upload_started, function(e, uploadXHR){
        running_uploads.push(uploadXHR);
        $cancel_button.css('visibility', 'visible');
    });

    $(document).on(GroupProjectCommon.Submission.events.upload_failed, handle_upload_end);
    $(document).on(GroupProjectCommon.Submission.events.upload_complete, handle_upload_end);

    $('.cancel_upload', element).on('click', function () {
        for (var i=0; i<running_uploads.length; i++) {
            var uploadXHR = running_uploads[i];
            uploadXHR.abort();
        }
        running_uploads = [];
        $cancel_button.css('visibility', 'hidden');
    });

    $(".check_submissions", element).click(function(){
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, "check_submissions"),
            data: JSON.stringify({}),
        });
    });
}

function GroupProjectNavigatorSubmissionsView(runtime, element) {
    const upload_started_event = 'group_project_v2.submission.upload_started';
    const upload_failed_event = 'group_project_v2.submission.upload_failed';
    const upload_complete_event = 'group_project_v2.submission.upload_complete';

    var running_uploads = [];

    $(document).on(upload_started_event, function(e, uploadXHR){
        running_uploads.push(uploadXHR);
    });

    $(document).on(upload_failed_event, function(e, uploadXHR) {
        var index = $.inArray(uploadXHR, running_uploads);
        if (index > -1) {
            running_uploads.splice(index, 1);
        }
    });

    $(document).on(upload_complete_event, function(e, uploadXHR) {
        var index = $.inArray(uploadXHR, running_uploads);
        if (index > -1) {
            running_uploads.splice(index, 1);
        }
    });

    $('.cancel_upload', element).on('click', function () {
        for (var i=0; i<running_uploads.length; i++) {
            var uploadXHR = running_uploads[i];
            uploadXHR.abort();
        }
        running_uploads = [];
    });
}

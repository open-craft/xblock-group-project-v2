function GroupProjectSubmissionBlock(runtime, element) {
    var failed_uploads = [];
    var current_upload = null;

    function uploadStarted(uploadXHR) {
        $(document).trigger('group_project_v2.submission.upload_started', uploadXHR);
    }

    function uploadFailed(uploadXHR){
        $(document).trigger('group_project_v2.submission.upload_failed', uploadXHR);
    }

    function uploadComplete(uploadXHR) {
        $(document).trigger('group_project_v2.submission.upload_complete', uploadXHR);
    }

    var upload_data = {
        dataType: 'json',
        url: runtime.handlerUrl(element, "upload_submission"),
        formData: [
            {
                name: 'csrfmiddlewaretoken',
                value: $.cookie('csrftoken')
            }
        ],
        add: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_name', target_form).val(data.files[0].name);
            $('.' + data.paramName + '_progress', target_form).css({width: '0%'}).removeClass('complete failed');
            $('.' + data.paramName + '_progress_box', target_form).css({visibility: 'visible'});

            $(document).one('perform_uploads', function (ev) {
                var uploadXHR = data.submit();
                uploadXHR
                    .success(function (data, textStatus, jqXHR) {
                        if (data.new_stage_states) {
                            for (var i=0; i<data.new_stage_states.length; i++) {
                                var new_state = data.new_stage_states[i];
                                $(document).trigger(
                                    "group_project_v2.project_navigator.stage_status_update",
                                    [new_state.activity_id, new_state.stage_id, new_state.state]
                                );
                            }
                        }

                        if (data.submissions) {
                            for (var submission_id in data.submissions) {
                                if (!data.submissions.hasOwnProperty(submission_id)) return;
                                var location = data.submissions[submission_id];
                                $('.' + submission_id + '_name', target_form).parent(".upload_item_wrapper")
                                    .data('location', location)
                                    .attr('data-location', location); // need to set attr here as there are css rules for [data-location] attribute
                            }
                        }

                        uploadComplete(jqXHR);
                    })
                    .fail(function (jqXHR, textStatus, errorThrown) {
                        uploadFailed(jqXHR);
                    });

                uploadStarted(uploadXHR);
            });

            $(document).trigger('perform_uploads');
        },
        progress: function (e, data) {
            var target_form = $(e.target);
            var percentage = parseInt(data.loaded / data.total * 100, 10);
            $('.' + data.paramName + '_progress', target_form).css('width', percentage + '%');
        },
        done: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_progress', target_form).css('width', '100%').addClass('complete');
            var input = $('.' + data.paramName + '_name', target_form);
            input.attr('data-original-value', input.val());
        },
        fail: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName[0] + '_progress', target_form).css('width', '100%').addClass('failed');
            failed_uploads.push(data.files[0].name);
            var message = data.jqXHR.responseJSON ? data.jqXHR.responseJSON.message : data.jqXHR.responseText;
            target_form.prop('title', message);
        }
    };

    $(".upload_item_wrapper", element).click(function(){
        var location = $(this).data('location');
        if (location) {
            window.open(location);
        }
    });

    if ($.fn.fileupload) {
        $('.uploader', element).fileupload(upload_data);
    }
}

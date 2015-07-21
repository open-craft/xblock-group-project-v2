function GroupProjectSubmissionBlock(runtime, element) {
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext == "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
    }

    function uploadStarted(uploadXHR) {
        $(document).trigger('group_project_v2.submission.upload_started', uploadXHR);
    }

    function uploadFailed(uploadXHR){
        $(document).trigger('group_project_v2.submission.upload_failed', uploadXHR);
    }

    function uploadComplete(uploadXHR) {
        $(document).trigger('group_project_v2.submission.upload_complete', uploadXHR);
    }

    var message_box = $(".message"); // searching globally - not a typo: message box is created at group project level
    function show_message(msg, title, title_css_class) {
        message_box.find('.message_text').html(msg);
        message_box.find('.message_title').html(title);
        if (title_css_class) {
            message_box.find('.message_title').addClass(title_css_class)
        }
        message_box.show();
    }

    function getMessageFromJson(jqXHR){
        return jqXHR.responseJSON ? jqXHR.responseJSON.message : jqXHR.responseText;
    }

    function getMessageTitleFromJson(jqXHR, default_title){
        return (jqXHR.responseJSON && jqXHR.responseJSON.title) ? jqXHR.responseJSON.title : default_title;
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
            var message = getMessageFromJson(data.jqXHR),
                title = getMessageTitleFromJson(data.jqXHR, gettext("Error"));
            show_message(message, title);
        },
        fail: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName[0] + '_progress', target_form).css('width', '100%').addClass('failed');
            var message = getMessageFromJson(data.jqXHR),
                title = getMessageTitleFromJson(data.jqXHR, gettext("Error"));
            target_form.prop('title', message);
            show_message(message, title, 'error');
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

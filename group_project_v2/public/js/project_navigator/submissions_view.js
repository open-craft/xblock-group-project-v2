function GroupProjectNavigatorSubmissionsView(runtime, element) {
    var failed_uploads = [];
    var current_upload = null;
    var $action_buttons = $(".action_buttons", element);

    function setCurrentUpload(uploadXHR) {
        current_upload = uploadXHR;
        $action_buttons.css('visibility', 'visible');
    }

    function clearCurentUpload(){
        current_upload = null;
        $action_buttons.css('visibility', 'hidden');
    }

    var upload_data = {
        dataType: 'json',
        url: runtime.handlerUrl(element, "upload_submission"),
        add: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_name', target_form).val(data.files[0].name);
            $('.' + data.paramName + '_progress', target_form).css({width: '0%'}).removeClass('complete failed');
            $('.' + data.paramName + '_progress_box', target_form).css({visibility: 'visible'});

            data.formData = getFormData(target_form);

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
                    });

                setCurrentUpload(uploadXHR);
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
            clearCurentUpload();
        },
        fail: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_progress', target_form).css('width', '100%').addClass('failed');
            failed_uploads.push(data.files[0].name);
            var message = data.jqXHR.responseJSON ? data.jqXHR.responseJSON.message : data.jqXHR.responseText;
            target_form.prop('title', message);
            clearCurentUpload();
        }
    };

    function getFormData(form) {
        var result = [
            {
                name: 'csrfmiddlewaretoken',
                value: $.cookie('csrftoken')
            }
        ];
        var additional_fields = ['activity_id', 'stage_id'];

        for (var i=0; i< additional_fields.length; i++) {
            var parameter_name = additional_fields[i],
                $field_input = $('.'+parameter_name, form);

            if ($field_input) {
                result.push({
                    name: parameter_name,
                    value: $field_input.val()
                });
            }
        }
        return result;
    }

    $(".upload_item_wrapper", element).click(function(){
        var location = $(this).data('location');
        if (location) {
            window.open(location);
        }
    });

    if ($.fn.fileupload) {
        $('.uploader', element).fileupload(upload_data);

        $('.cancel_upload', element).on('click', function () {
            if (current_upload) {
                current_upload.abort();
                clearCurentUpload();
            }
        });

        $('.show_upload_form', element).on('click', function () {
            // upload button initially disabled
            $('.do_upload', element).prop('disabled', true).css('cursor', 'not-allowed');
            $('.file-progress-box', element).css('visibility', 'hidden');
            $('.file-progress', element).removeClass('complete failed');

            // reset file input fields
            var fields = element.find('.upload_item input');
            fields.each(function (i, v) {
                var field = $(v);
                field.val(field.attr('data-original-value'));
            });

            element.show();
        });
    }
}

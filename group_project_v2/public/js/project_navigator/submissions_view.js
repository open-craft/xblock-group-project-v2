function GroupProjectNavigatorSubmissionsView(runtime, element) {
    var failed_uploads = [];
    var upload_data = {
        dataType: 'json',
        url: runtime.handlerUrl(element, "upload_submission"),
        add: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_name', target_form).val(data.files[0].name);
            $('.' + data.paramName + '_progress', target_form).css({width: '0%'}).removeClass('complete failed');
            $('.' + data.paramName + '_progress_box', target_form).css({visibility: 'visible'});

            data.formData = getFormData();

            $(document).one('perform_uploads', function (ev) {
                data.submit();
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
            $('.' + data.paramName + '_progress', target_form).css('width', '100%').addClass('failed');
            failed_uploads.push(data.files[0].name);
            var message = data.jqXHR.responseJSON ? data.jqXHR.responseJSON.message : data.jqXHR.responseText;
            target_form.prop('title', message);
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

    if ($.fn.fileupload) {
        $('.uploader', element).fileupload(upload_data);

        $('.cancel_upload', element).on('click', function () {
            element.hide();
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

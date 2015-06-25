function GroupProjectNavigatorSubmissionsView(runtime, element) {
    var failed_uploads = [];
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
        stop: function (e) {
            $('.do_upload', element).prop('disabled', true).css('cursor', 'not-allowed');
            $('.group_submissions', element).empty();
            $.ajax({
                url: runtime.handlerUrl(element, "refresh_submission_links"),
                dataType: 'json',
                success: function (data) {
                    $('.submission-links-wrapper', element).html(data.html);
                },
                error: function (data) {
                    console.log(data);
                }
            });

            if (failed_uploads.length <= 0) {
                setTimeout(function () {
                    element.hide();
                }, 1000);
            }
            failed_uploads = [];
        },
        fail: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName + '_progress', target_form).css('width', '100%').addClass('failed');
            failed_uploads.push(data.files[0].name);
            var message = data.jqXHR.responseJSON ? data.jqXHR.responseJSON.message : data.jqXHR.responseText;
            target_form.prop('title', message);
        }
    };

    if ($.fn.fileupload) {
        debugger;
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

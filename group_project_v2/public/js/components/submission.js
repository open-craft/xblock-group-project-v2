/* global GroupProjectCommon */
/* exported GroupProjectSubmissionBlock */
function GroupProjectSubmissionBlock(runtime, element) {
    "use strict";

    /**
     * This function is responsible for formatting the modal dialog for user.
     */
    function prepareMessageObject(jqXHR, default_title){

        function getMessageFromJson(jqXHR){
            return jqXHR.responseJSON ? jqXHR.responseJSON.message : jqXHR.responseText;
        }

        function getMessageTitleFromJson(jqXHR, default_title) {
            return (jqXHR.responseJSON && jqXHR.responseJSON.title) ? jqXHR.responseJSON.title : default_title;
        }

        function filterMessageObject(message){
            function htmlencode(html) {
                return document.createElement('span')
                    .appendChild(document.createTextNode(html))
                    .parentNode.innerHTML;
            }

            if(message.status === 0 && message.statusText === 'abort') {
                message.title = GroupProjectCommon.gettext('Upload cancelled.');
                message.content = GroupProjectCommon.gettext('Upload cancelled by user.');
            }
            if (message.status === 400) {
                // Hotfix for XSS reflection through the file validator error messages
                message.title = htmlencode(message.title);
                message.content = htmlencode(message.content);
            }
            if (message.status === 403) {
                var base_message = GroupProjectCommon.gettext(
                    "An error occurred while uploading your file. Please " +
                    "refresh the page and try again. If it still does not " +
                    "upload, please contact your Course TA."
                );
                var technical_details = '';
                // Exact CSRF response message may vary, and may be different
                // between different environments. We can assume that it should
                // contain CSRF string.
                if (message.content.indexOf('CSRF') !== -1){
                    technical_details += GroupProjectCommon.gettext(' Technical details: CSRF verification failed.');
                }else{
                    technical_details += GroupProjectCommon.gettext(' Technical details: 403 error.');
                }

                message.content = "<p>" + base_message + "</p><p>" + technical_details + "</p>";
            }
            return message;
        }

        if (typeof jqXHR.responseJSON === 'undefined'){
            // This is inconsistency between Apros and Workbench, in Apros
            // requests have responseJSON and in Workbench do not.
            try {
                jqXHR.responseJSON = $.parseJSON(jqXHR.responseText);
            } catch (e){
                jqXHR.responseJSON = null;
            }
        }

        var message = {
            "status": jqXHR.status,
            "statusText": jqXHR.statusText,
            "content": getMessageFromJson(jqXHR),
            "title": getMessageTitleFromJson(jqXHR, default_title)
        };

        message = filterMessageObject(message);

        return message;
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
        pasteZone: null,
        add: function (e, data) {
            var target_form = $(e.target),
                parentData = data;
            $('.' + data.paramName + '_name', target_form).val(data.files[0].name);
            $('.' + data.paramName + '_progress', target_form).css({width: '0%'}).removeClass('complete failed');
            $('.' + data.paramName + '_progress_box', target_form).css({visibility: 'visible'});

            $(document).one('perform_uploads', function () {
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
                                $('.' + parentData.paramName + '_uploaded_by', element).html(
                                    GroupProjectCommon.gettext('Uploaded by ') + data.user_label +
                                     ' on ' + data.submission_date);
                            }
                        }

                        if (data.submissions) {
                            for (var submission_id in data.submissions) {
                                if (data.submissions.hasOwnProperty(submission_id)) {
                                    var location = data.submissions[submission_id];
                                    $('.' + submission_id + '_name', target_form).parent(".upload_item_wrapper")
                                        .data('location', location)
                                        .attr('data-location', location); // need to set attr as there are css rule
                                }
                            }
                        }

                        $(document).trigger(GroupProjectCommon.Submission.events.upload_complete, jqXHR);
                    })
                    .fail(function (jqXHR) {
                        $(document).trigger(GroupProjectCommon.Submission.events.upload_failed, jqXHR);
                    });

                $(document).trigger(GroupProjectCommon.Submission.events.upload_started, uploadXHR);
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
            var message = prepareMessageObject(data.jqXHR, GroupProjectCommon.gettext("Error"));
            GroupProjectCommon.Messages.show_message(message.content, message.title);
        },
        fail: function (e, data) {
            var target_form = $(e.target);
            $('.' + data.paramName[0] + '_progress', target_form).css('width', '100%').addClass('failed');
            var message = prepareMessageObject(data.jqXHR, GroupProjectCommon.gettext("Error"));
            target_form.prop('title', message.message);
            GroupProjectCommon.Messages.show_message(message.content, message.title, 'error');
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

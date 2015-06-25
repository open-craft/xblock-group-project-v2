// TODO: this function does way too much: might make sense to extract reviews, assessments, etc.
// into separate functions and make this function call them
function GroupProjectBlock(runtime, element) {

    var get_from_node = function (selector, default_value) {
        var the_node = $(selector, element);
        return (the_node.length > 0) ? the_node.html() : default_value;
    };
    var DATA_PRESENT_SUBMIT = get_from_node('.data-present-button-text', 'Resubmit');
    var NO_DATA_PRESENT_SUBMIT = get_from_node('.no-data-button-text', 'Submit');

    var message_box = $('.message', element).appendTo($(document.body));
    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
    })

    var show_message = function (msg) {
        message_box.find('.message_text').html(msg);
        message_box.show();
    }

    var mean = function (value_array) {
        var sum = 0;
        var count = value_array.length;
        if (count < 1) {
            return null;
        }

        for (var i = 0; i < count; ++i) {
            sum += parseFloat(value_array[i]);
        }

        return sum / count;
    }

    var load_data_into_form = function (form_node, data_for_form) {
        form_node.find('.answer').val(null);
        for (data_item in data_for_form) {
            form_node.find('button.submit').html(DATA_PRESENT_SUBMIT);
            // NOTE: use of ids specified by designer here
            var $form_item = form_node.find("#" + data_item);
            $form_item.val(data_for_form[data_item]);
        }
        validate_form_answers(form_node);
    }

    var load_my_feedback_data = function (section_node, data) {
        // Clean existing values
        $('.feedback-data', section_node).remove();

        for (data_item in data) {
            // either a place witin to list it or the outer location
            var fill_field = $('#list_' + data_item, section_node);
            if (fill_field.length < 1) {
                fill_field = $('#assess_' + data_item, section_node);
            }
            var data_class = fill_field.data('class');

            for (var i = 0; i < data[data_item].length; ++i) {
                var node = $("<div class='feedback-data' />");
                if (data_class && data_class.length > 0) {
                    node.addClass(data_class);
                }
                node.html(data[data_item][i]);
                fill_field.append(node);
            }

            var mean_field = $('#mean_' + data_item, section_node);
            mean_field.text(Math.round(mean(data[data_item])));
        }
    }

    var _load_data = function (handler_name, args, form_node, post_data_fn) {
        $('.group-project-xblock-wrapper', element).addClass('waiting');
        form_node.find('.editable').attr('disabled', 'disabled');
        form_node.find('.answer').val(null);
        form_node.find('button.submit').html(NO_DATA_PRESENT_SUBMIT).attr('disabled', 'disabled');
        $.ajax({
            url: runtime.handlerUrl(element, handler_name),
            data: args,
            dataType: 'json',
            success: function (data) {
                if (data.result && data.result == "error") {
                    if (data.msg) {
                        show_message(data.msg);
                    }
                    else {
                        show_message('We encountered an error loading feedback.');
                    }
                }
                else {
                    post_data_fn(form_node, data);
                }
            },
            error: function (data) {
                show_message('We encountered an error loading feedback.');
            }
        }).done(function () {
            $('.group-project-xblock-wrapper', element).removeClass('waiting');
            form_node.find('.editable').removeAttr('disabled');
        });
    }

    var load_data_for_peer = function (peer_id) {
        _load_data('load_peer_feedback', 'peer_id=' + peer_id, $('.peer_review', element), load_data_into_form);
    }

    var load_data_for_other_group = function (group_id) {
        _load_data('load_other_group_feedback', 'group_id=' + group_id, $('.other_group_review', element), load_data_into_form);
    }

    $('form.peer_review, form.other_group_review', element).on('submit', function (ev) {
        ev.preventDefault();
        var $form = $(this);

        $form.find(':submit').prop('disabled', true);
        items = $form.serializeArray();
        data = {}
        $.each(items, function (i, v) {
            data[v.name] = v.value;
        });

        $.ajax({
            type: $form.attr('method'),
            url: runtime.handlerUrl(element, $form.attr('action')),
            data: JSON.stringify(data),
            success: function (data) {
                var msg = 'Thanks for your feedback!';
                if (data.msg) {
                    msg = data.msg;
                }
                show_message(msg);
            },
            error: function (data) {
                show_message('We encountered an error saving your feedback.');
            },
            complete: function (data) {
                $form.find(':submit').prop('disabled', false).html(DATA_PRESENT_SUBMIT);
            }
        });

        return false;
    });

    var peers = JSON.parse($('.peer_group', element).html());
    var peer_node = function (peer) {
        var pn = $('<a class="select_peer" />');
        var pi = $('<img class="avatar" />');
        if (peer.avatar_url) {
            pi.attr('src', peer.avatar_url);
        }
        pn.attr('title', peer.username);
        pn.data('id', peer.id);
        pn.data('username', peer.username)
        pn.append(pi);

        return pn;
    }

    // .peers is placeholder elem to inject list of peers to - it must be present in project XML if peer review is enabled
    for (var i = 0; i < peers.length; ++i) {
        $('.peers', element).append(peer_node(peers[i]));
    }

    var groups = JSON.parse($('.assess_groups', element).html());
    var group_node = function (group) {
        var gn = $('<a class="select_group" />');
        var gi = $('<span class="avatar"><i class="fa fa-users mk-icon-groupworknav" /></span>');
        gn.data('id', group.id);
        gn.append(gi);

        return gn;
    }

    // .other_groups is placeholder elem to inject list of groups to - it must be present in project XML if group review is enabled
    for (var i = 0; i < groups.length; ++i) {
        $('.other_groups', element).append(group_node(groups[i]));
    }

    var validate_form_answers = function (form_node) {
        var answers = form_node.find('.required .answer');
        var submitButton = form_node.find('button.submit');
        var check_answered_total = function (answers, submitButton) {
            // TODO: unintentional global variable answers_checked
            var answers_total = answers_checked = 0;
            submitButton.attr('disabled', 'disabled');
            $.each(answers, function () {
                if ($(this).is('textarea')) {
                    answers_total += 1;
                    if ($(this).val() !== '') {
                        answers_checked += 1;
                    }
                }
                else if ($(this).is('select')) {
                    answers_total += 1;
                    if ($(this).find('option:selected').attr('value') !== '') {
                        answers_checked += 1;
                    }
                }
            });
            if (answers_total === answers_checked) {
                submitButton.attr('disabled', false);
            }
        };

        check_answered_total(answers, submitButton);

        answers.on('change keyup paste', function () {
            check_answered_total(answers, submitButton);
        });
    };

    var step_map = JSON.parse($('.step_map', element).html());

    $(document).on('select_stage', function (target, selected_step_id) {
        $('.activity_section').hide();

        // NOTE: use of ids specified by designer here
        $('#activity_' + selected_step_id).show();

        // Update step makers
        var step_pn = step_map[selected_step_id];
        $('.page-to.previous, .page-to.next', element).attr('title', '').off('click').removeAttr('href');

        // TODO: almost identical blocks: extract method
        if (step_pn.prev) {
            var prev = step_map[step_pn.prev];
            $('.page-to.previous', element)
                .attr('title', prev.name)
                .on('click', function () {
                    $("#" + step_pn.prev).click();
                }).attr('href', '#');
        }
        if (step_pn.next) {
            var next_step = step_map[step_pn.next];
            if (next_step['restrict_message']) {
                $('.page-to.next', element).attr('title', next_step['restrict_message']);
            }
            else {
                $('.page-to.next', element)
                    .attr('title', next_step.name)
                    .on('click', function () {
                        $("#" + step_pn["next"]).click();
                    }).attr('href', '#');
            }
        }
    });

    $('.view_feedback').on('click', function (ev) {
        var showid = $(this).data('showid');

        var operation = (showid == "cohort_feedback") ? 'load_my_group_feedback' : 'load_my_peer_feedback';
        var selector = (showid == "cohort_feedback") ? '.group_assessment' : '.peer_assessment';

        _load_data(operation, null, $(selector, element), load_my_feedback_data);
        $(selector, element).show();

        $(document).trigger('data_loaded', {operation: operation});
        ev.preventDefault();
        return false;
    });

    $('.select_peer,.select_group').on('click', function (ev) {
        var $this = $(this);
        var is_peer = $this.hasClass('select_peer');
        $('.select_peer,.select_group').removeClass('selected'); // removing selection from other peers/groups. NOT a bug
        $this.addClass('selected');

        var load_operation = load_data_for_peer;
        var operation_name = 'load_data_for_peer';
        var id_field_selector = '.peer_id';
        if (is_peer) {
            $('.username', element).text($this.data('username'));
        }
        else {
            id_field_selector = '.group_id';
            load_operation = load_data_for_other_group;
            operation_name = 'load_data_for_other_group';
            $('.other_submission_links', element).empty().hide();
        }

        $(id_field_selector, element).attr('value', $this.data('id'));
        load_operation($this.data('id'));

        $(document).trigger('data_loaded', {operation: operation_name, data_for: $this.data('id')});
        ev.preventDefault();
        return false;
    });

    // activate the first step
    $(document).trigger("steps_available", step_map);
    $(document).trigger("select_stage", step_map["default"]);

    var upload_form = $('.upload_form', element).appendTo($(document.body));
    var failed_uploads = [];

    // TODO: extract class/object?
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
            $('.' + data.paramName + '_label', target_form).text("Update");
            $('.' + data.paramName + '_progress', target_form).css({width: '0%'}).removeClass('complete failed');
            $('.' + data.paramName + '_progress_box', target_form).css({visibility: 'visible'});

            $(document).one('perform_uploads', function (ev) {
                data.submit();
            });

            // enable upload button & reset progress
            $('.do_upload', upload_form).prop('disabled', false).css('cursor', 'pointer');
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
            $('.do_upload', upload_form).prop('disabled', true).css('cursor', 'not-allowed');
            $('.group_submissions', element).empty();
            $.ajax({
                url: runtime.handlerUrl(element, "refresh_submission_links"),
                dataType: 'json',
                success: function (data) {
                    $('.group_submissions', element).html(data.html);
                },
                error: function (data) {
                    show_message('We encountered an error.');
                }
            });

            if (failed_uploads.length <= 0) {
                setTimeout(function () {
                    upload_form.hide();
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

    var review_submissions_dialog = $('.review_submissions_dialog', element).appendTo($(document.body));
    $('.view_other_submissions', element).on('click', function () {
        var $content = $('.other_submission_links', review_submissions_dialog);
        $content.empty().hide();
        var selected_group_id = $('.select_group.selected').data("id");
        $.ajax({
            url: runtime.handlerUrl(element, "other_submission_links"),
            data: {group_id: selected_group_id},
            dataType: 'json',
            success: function (data) {
                $content.html(data.html).show();
                review_submissions_dialog.show();
            },
            error: function (data) {
                show_message('We encountered an error.');
            }
        });
    });
    $('.close_review_dialog', review_submissions_dialog).on('click', function () {
        review_submissions_dialog.hide();
    });

    if ($.fn.fileupload) {
        $('.uploader', upload_form).fileupload(upload_data);

        $('.cancel_upload', upload_form).on('click', function () {
            upload_form.hide();
        });
        $('.do_upload', upload_form).on('click', function () {
            $('.do_upload', upload_form).prop('disabled', true).css('cursor', 'wait');
            $(document).trigger('perform_uploads');
        });

        $('.show_upload_form', element).on('click', function () {
            // upload button initially disabled
            $('.do_upload', upload_form).prop('disabled', true).css('cursor', 'not-allowed');
            $('.file-progress-box', upload_form).css('visibility', 'hidden');
            $('.file-progress', upload_form).removeClass('complete failed');

            // reset file input fields
            var fields = upload_form.find('.upload_item input');
            fields.each(function (i, v) {
                var field = $(v);
                field.val(field.attr('data-original-value'));
            });

            upload_form.show();
        });

        // Activate the first peer, or the first group if no peers
        $(function () {
            var select_from = $('.select_peer, .select_group');
            if (select_from.length > 0) {
                select_from[0].click();
            }
        })
    }
    // TODO: a bit hacky solution to allow directly to stages
    // Remove when stages become actual XBlocks and jump_to_id supports jumping to children
    $(document).trigger('activity_initialized', element);
}

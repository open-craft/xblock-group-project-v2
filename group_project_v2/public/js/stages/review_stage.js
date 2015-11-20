function GroupProjectReviewStage(runtime, element) {
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext == "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
    }

    var DATA_PRESENT_SUBMIT = gettext('Resubmit');
    var NO_DATA_PRESENT_SUBMIT = gettext('Submit');

    var SELECT_PEER_TO_REVIEW = gettext("Please select Teammate to review");
    var SELECT_GROUP_TO_REVIEW = gettext("Please select Group to review");

    var $form = $(".review",  element);
    var $submit_btn = $form.find('button.submit');
    var is_peer_review = $form.data('review-type') == 'peer_review';
    var group_project_dom = $(element).parents(".group-project-xblock-wrapper");
    var message_box = $(".message", group_project_dom);

    function show_message(msg) {
        message_box.find('.message_text').html(msg);
        message_box.show();
    }

    function validate_form_answers() {
        var answers = $form.find('.required .answer');
        var submitButton = $form.find('button.submit');

        function check_answered_total(answers, submitButton) {
            var answers_total, answers_checked;
            answers_total = answers_checked = 0;
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
        }

        check_answered_total(answers, submitButton);

        answers.on('change keyup paste', function () {
            check_answered_total(answers, submitButton);
        });
    }

    function load_data_into_form(data_for_form) {
        $form.find('.answer').val(null);
        for (var data_item in data_for_form) {
            if (!data_for_form.hasOwnProperty(data_item)) continue;
            $form.find('button.submit').html(DATA_PRESENT_SUBMIT);
            // NOTE: use of ids specified by designer here
            var $form_item = $form.find("#" + data_item);
            $form_item.val(data_for_form[data_item]);
        }
        validate_form_answers();
    }

    function load_data_for_peer(peer_id) {
        _load_data('load_peer_feedback', 'peer_id=' + peer_id, $('.peer_review', element));
    }

    function load_data_for_other_group(group_id) {
        _load_data('load_other_group_feedback', 'group_id=' + group_id, $('.other_group_review', element));
    }

    function _load_data(handler_name, args) {
        $('.group-project-xblock-wrapper', element).addClass('waiting');
        $form.find('.editable').attr('disabled', 'disabled');
        $form.find('.answer').val(null);
        $form.find('button.submit').html(NO_DATA_PRESENT_SUBMIT).attr('disabled', 'disabled');
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
                        show_message(gettext('We encountered an error loading feedback.'));
                    }
                }
                else {
                    load_data_into_form(data);
                }
            },
            error: function (data) {
                show_message(gettext('We encountered an error loading feedback.'));
            }
        }).done(function () {
            $('.group-project-xblock-wrapper', element).removeClass('waiting');
            $form.find('.editable').removeAttr('disabled');
        });
    }

    $('.select_peer,.select_group', element).on('click', function (ev) {
        var $this = $(this);
        var is_peer = $this.hasClass('select_peer');
        $('.select_peer,.select_group').removeClass('selected'); // removing selection from other peers/groups. NOT a bug
        $this.addClass('selected');

        var load_operation = load_data_for_peer;
        var operation_name = 'load_data_for_peer';
        if (is_peer) {
            $('.username', element).text($this.data('username'));
        }
        else {
            load_operation = load_data_for_other_group;
            operation_name = 'load_data_for_other_group';
            $('.other_submission_links', element).empty().hide();
        }

        load_operation($this.data('id'));

        $(document).trigger('data_loaded', {operation: operation_name, data_for: $this.data('id')});
        ev.preventDefault();
        return false;
    });

    $submit_btn.on('click', function (ev) {
        ev.preventDefault();

        $form.find(':submit').prop('disabled', true);
        var items = $form.find('input, select, textarea').serializeArray();
        var data = {};
        $.each(items, function (i, v) {
            data[v.name] = v.value;
        });
        data["review_subject_id"] = $("ul.review_subjects li.selected", $form).data('id');

        if (!data["review_subject_id"]) {
            var message = is_peer_review ? SELECT_PEER_TO_REVIEW : SELECT_GROUP_TO_REVIEW;
            show_message(message);
            return;
        }

        $.ajax({
            type: $form.data('method'),
            url: runtime.handlerUrl(element, $form.data('action')),
            data: JSON.stringify(data),
            success: function (data) {
                var msg = (data.msg) ? data.msg : gettext('Thanks for your feedback!');
                show_message(msg);

                if (data.new_stage_states) {
                    for (var i=0; i<data.new_stage_states.length; i++) {
                        var new_state = data.new_stage_states[i];
                        $(document).trigger(
                            "group_project_v2.project_navigator.stage_status_update",
                            [new_state.activity_id, new_state.stage_id, new_state.state]
                        );
                    }
                }
            },
            error: function (data) {
                show_message(gettext('We encountered an error saving your feedback.'));
            },
            complete: function (data) {
                $form.find(':submit').prop('disabled', false).html(DATA_PRESENT_SUBMIT);
            }
        });

        return false;
    });

    var review_submissions_dialog = $('.review_submissions_dialog', element);
    $('.view_other_submissions', element).on('click', function () {
        var $content = $('.other_submission_links', review_submissions_dialog);
        $content.empty().hide();
        var selected_group_id = $(this).parents(".select_group").data("id");
        if (!selected_group_id) {
            return;
        }
        $.ajax({
            url: runtime.handlerUrl(element, "other_submission_links"),
            data: {group_id: selected_group_id},
            dataType: 'json',
            success: function (data) {
                $content.html(data.html).show();
                review_submissions_dialog.show();
            },
            error: function (data) {
                show_message(gettext('We encountered an error.'));
            }
        });
    });

    $('.close_review_dialog', review_submissions_dialog).on('click', function () {
        review_submissions_dialog.hide();
    });

    if ($('.select_peer.selected,.select_group.selected', element).length === 0) {
        $form.find('.editable').attr('disabled', 'disabled');
        $form.find('.answer').val(null);
        $submit_btn.attr('disabled', 'disabled');
    }
    $(element).ready(function () {
        var options = $('.select_peer,.select_group', element);
        if (options.length) {
            options[0].click();
        }
    })
}

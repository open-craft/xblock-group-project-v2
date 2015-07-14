function ReviewStageXBlock(runtime, element) {
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext == "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
        window.ngettext = function ngettext_stub(strA, strB, n) { return n == 1 ? strA : strB; };
    }

    var DATA_PRESENT_SUBMIT = gettext('Resubmit');
    var NO_DATA_PRESENT_SUBMIT = gettext('Submit');

    var SELECT_PEER_TO_REVIEW = gettext("Please select Teammate to review");
    var SELECT_GROUP_TO_REVIEW = gettext("Please select Group to review");

    var $form = $("form.review",  element);
    var is_peer_review = $form.data('review-type') == 'peer_review';
    var message_box = $(".message"); // searching globally - not a typo: message box is created at group project level

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

    $form.on('submit', function (ev) {
        ev.preventDefault();

        $form.find(':submit').prop('disabled', true);
        var items = $form.serializeArray();
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
            type: $form.attr('method'),
            url: runtime.handlerUrl(element, $form.attr('action')),
            data: JSON.stringify(data),
            success: function (data) {
                var msg = (data.msg) ? data.msg : gettext('Thanks for your feedback!');
                show_message(msg);
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

    var review_submissions_dialog = $('.review_submissions_dialog', element).appendTo($(document.body));
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
}

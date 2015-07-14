function GroupProjectCompletionStage(runtime, element) {
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext == "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
    }

    var $form = $(".group-project-completion-form", element);
    var message_box = $(".message"); // searching globally - not a typo: message box is created at group project level

    function show_message(msg) {
        message_box.find('.message_text').html(msg);
        message_box.show();
    }

    $(".group-project-completion-checkmark", element).click(function(ev) {
        ev.preventDefault();
        if (!$(this)[0].checked) {
            return false;
        }

        $.ajax({
            type: $form.attr('method'),
            url: runtime.handlerUrl(element, $form.attr('action')),
            data: JSON.stringify({}),
            success: function (data) {
                var msg = (data.msg) ? data.msg : gettext('Stage completed!');
                show_message(msg);

                if (data.result == 'error'){
                    return;
                }

                $(this).prop('checked', 'checked');
                $(this).prop('disabled', 'disabled');

                if (data.new_stage_states) {
                    for (var i = 0; i < data.new_stage_states.length; i++) {
                        var new_state = data.new_stage_states[i];
                        $(document).trigger(
                            "group_project_v2.project_navigator.stage_status_update",
                            [new_state.activity_id, new_state.stage_id, new_state.state]
                        );
                    }
                }
            },
            error: function (data) {
                var msg = (data.msg) ? data.msg : gettext('We encountered an error saving your progress.');
                show_message(msg);
            }
        });
    })
}
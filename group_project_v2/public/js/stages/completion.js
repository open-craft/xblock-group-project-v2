/* exported GroupProjectCompletionStage */
function GroupProjectCompletionStage(runtime, element) {
    "use strict";
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext === "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
    }

    var $form = $(".group-project-completion-form", element);
    var group_project_dom = $(element).parents(".group-project-xblock-wrapper");
    var message_box = $(".message", group_project_dom);

    function show_message(msg) {
        message_box.find('.message_text').html(msg);
        message_box.show();
    }

    $(".group-project-completion-checkmark", element).click(function(ev) {
        var checkbox = this;
        ev.preventDefault();
        if (!$(this)[0].checked) {
            return false;
        }

        $.ajax({
            type: $form.attr('method'),
            url: runtime.handlerUrl(element, $form.attr('action')),
            data: JSON.stringify({}),
            success: function (data) {
                var msg = (data.msg) ? data.msg : gettext('This task has been marked as complete.');
                show_message(msg);

                if (data.result === 'error'){
                    return;
                }

                $(checkbox).prop('checked', true);
                $(checkbox).prop('disabled', true);

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
    });
}

/* global GroupProjectCommon */
/* exported GroupProjectCompletionStage */
function GroupProjectCompletionStage(runtime, element) {
    "use strict";
    var $form = $(".group-project-completion-form", element);

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
                var msg = (data.msg) ? data.msg : GroupProjectCommon.CompletionStage.messages.MARKED_AS_COMPLETE;
                GroupProjectCommon.Messages.show_message(msg);

                if (data.result === 'error'){
                    return;
                }

                $(checkbox).prop('checked', true);
                $(checkbox).prop('disabled', true);

                if (data.new_stage_states) {
                    for (var i = 0; i < data.new_stage_states.length; i++) {
                        var new_state = data.new_stage_states[i];
                        $(document).trigger(
                            GroupProjectCommon.ProjectNavigator.events.stage_status_update,
                            [new_state.activity_id, new_state.stage_id, new_state.state]
                        );
                    }
                }
            },
            error: function (data) {
                var msg = (data.msg) ? data.msg : GroupProjectCommon.CompletionStage.messages.ERROR_SAVING_PROGRESS;
                GroupProjectCommon.Messages.show_message(msg);
            }
        });
    });
}

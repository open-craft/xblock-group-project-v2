// TODO: this function does way too much: might make sense to extract reviews, assessments, etc.
// into separate functions and make this function call them
function GroupProjectBlock(runtime, element) {
    var message_box = $('.message', element).appendTo($(document.body));
    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
    });

    // TODO: does not include activity_id - might need fixing when all activities are displayed simultaneously
    $(document).on('select_stage', function (target, selected_stage_id) {
        // can't use $('#'+selected_stage_id) as selected_stage_id contains slashes
        var stage = $("[id='"+selected_stage_id+"']", element);
        if (stage.length > 0) {
            $('.activity_section', element).hide();
            stage.show();
        }
    });

    var initialization_data = JSON.parse($('.initialization_data', element).html());
    if (initialization_data && initialization_data.default_stage_id) {
        $(document).trigger('select_stage', initialization_data.default_stage_id);
    }


    // TODO: a bit hacky solution to allow directly to stages
    // Remove when stages become actual XBlocks and jump_to_id supports jumping to children
    $(document).trigger('activity_initialized', element);
}

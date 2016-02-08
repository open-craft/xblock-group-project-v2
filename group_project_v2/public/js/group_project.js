/* global GroupProjectCommon */
/* exported GroupProjectBlock */
function GroupProjectBlock(runtime, element) {
    "use strict";
    var message_box = $('.message', element);
    var discussion_box = $("#group-project-discussion", element);

    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
        message_box.find('.message_text').html("");
        message_box.find('.message_title').html("");
        message_box.find('.message_title').removeClass().addClass("message_title");
    });

    function show_message(msg, title, title_css_class) {
        message_box.find('.message_text').html(msg);
        message_box.find('.message_title').html(title);
        if (title_css_class) {
            message_box.find('.message_title').addClass(title_css_class);
        }
        message_box.show();
    }

    $(".group-project-static-content-block .block-link").click(function(ev) {
        // intercepting local jumps to PN Views - they should be rendered already,
        // so it's better to just activate them rather do a full-page reload (and navigate away from stage)
        ev.preventDefault();
        var target_block_id = $(this).data("target-block-id");

        $(document).trigger(GroupProjectCommon.ProjectNavigator.events.activate_view, target_block_id);
    });

    $(document).on(GroupProjectCommon.Discussion.events.show_discussion, function(){
        discussion_box.show();
    });

    $(document).on(GroupProjectCommon.Messages.events.show_message, function(event, event_data) {
        show_message(event_data.message, event_data.title, event_data.title_css_class);
    });

    discussion_box.find('.close-box, .modal-bg').click(function(){
        $(this).parents("#group-project-discussion").hide();
        $(document).trigger(GroupProjectCommon.Discussion.events.hide_discussion);
    });
}

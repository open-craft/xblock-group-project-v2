function GroupProjectBlock(runtime, element) {
    const activate_project_nav_view_event = 'group_project_v2.project_navigator.activate_view';
    const show_group_project_discussion = 'group_project_v2.discussion.show';
    const hide_group_project_discussion = 'group_project_v2.discussion.hide';

    var message_box = $('.message', element);
    var discussion_box = $("#group-project-discussion", element);

    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
        message_box.find('.message_text').html("");
        message_box.find('.message_title').html("");
        message_box.find('.message_title').removeClass().addClass("message_title");
    });

    $(".group-project-static-content-block .block-link").click(function(ev) {
        // intercepting local jumps to PN Views - they should be rendered already,
        // so it's better to just activate them rather do a full-page reload (and navigate away from stage)
        ev.preventDefault();
        var target_block_id = $(this).data("target-block-id");

        $(document).trigger(activate_project_nav_view_event, target_block_id);
    });

    $(document).on(show_group_project_discussion, function(){
        discussion_box.show();
    });

    discussion_box.find('.close-box, .modal-bg').click(function(){
        $(this).parents("#group-project-discussion").hide();
        $(document).trigger(hide_group_project_discussion);
    });
}

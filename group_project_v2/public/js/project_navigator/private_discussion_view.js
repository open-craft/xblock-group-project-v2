function GroupProjectPrivateDiscussionView(runtime, element) {
    var show_group_project_discussion = 'group_project_v2.discussion.show';

    $(".view-selector-item", element).click(function(){
        $(document).trigger(show_group_project_discussion);
    });
}

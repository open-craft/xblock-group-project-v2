function GroupProjectPrivateDiscussionView(runtime, element) {
    const show_group_project_discussion = 'group_project_v2.discussion.show';

    debugger;
    $(".view-selector-item", element).click(function(){
        $(document).trigger(show_group_project_discussion);
    });
}
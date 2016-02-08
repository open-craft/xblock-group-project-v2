/* global GroupProjectCommon */
/* exported GroupProjectPrivateDiscussionView */
function GroupProjectPrivateDiscussionView(runtime, element) {
    "use strict";
    $(".view-selector-item", element).click(function(){
        GroupProjectCommon.Discussion.show_discussion();
    });
}

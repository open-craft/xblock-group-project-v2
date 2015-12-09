/* exported GroupProjectNavigatorNavigationView */
function GroupProjectNavigatorNavigationView(runtime, element) {
    "use strict";
    $(document).on(
        'group_project_v2.project_navigator.stage_status_update',
        function(target, activity_id, stage_id, new_state) {
            var activity_wrapper = $(".group-project-activity-wrapper[data-activity-id='"+activity_id+"']", element),
                stage_item = $(".group-project-stage[data-stage-id='"+stage_id+"']", activity_wrapper);

            if (!stage_item) {
                return;
            }

            var status_icon = $(".group-project-stage-state", stage_item);
            status_icon.removeClass("not-started incomplete completed");
            status_icon.addClass(new_state);
        }
    );
}

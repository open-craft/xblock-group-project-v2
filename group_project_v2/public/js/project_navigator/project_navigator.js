/* global GroupProjectCommon */
/* exported GroupProjectNavigatorBlock */
function GroupProjectNavigatorBlock(runtime, element, initialization_args) {
    "use strict";
    var initial_view = 'navigation';
    var selector_item_query = ".group-project-navigator-view-selector .view-selector-item";
    var view_elements = $(".group-project-navigator-view", element),
        views = {},
        selected_view = null,
        initial_selected_view = initialization_args.selected_view;

    function switch_to_view(target_view, skip_content_switching) {
        var view_data = views[target_view];
        $(document).trigger(
            GroupProjectCommon.ProjectNavigator.events.switch_view, {new_view: target_view, old_view: selected_view}
        );

        selected_view = target_view;

        $(selector_item_query, element).removeClass('active');
        view_data.selector.addClass('active');

        if (!skip_content_switching) {
            $(".group-project-navigator-view", element).hide();
            view_data.view.show();
        }
    }

    $(selector_item_query, element).click(function(e){
        e.preventDefault();
        var view_type = $(this).data("view-type");

        if (!views.hasOwnProperty(view_type)) {
            // Unknown view
            return;
        }

        switch_to_view(view_type, $(this).data('skip-content'));
    });

    $(".group-project-navigator-view-close").click(function(){
        switch_to_view(initial_view);
    });

    $(document).on(GroupProjectCommon.ProjectNavigator.events.activate_view, function(target, target_block_id) {
        var escaped_block_id = target_block_id.replace(/\//g, ";_");
        var target_block = $("[data-view-id='"+escaped_block_id+"']");
        if (target_block) {
            switch_to_view(target_block.data('view-type'));
        }
    });

    $(document).on(GroupProjectCommon.Discussion.events.hide_discussion, function(){
        switch_to_view(initial_view);
    });

    for (var i=0; i<=view_elements.length; i++) {
        var view_element = $(view_elements[i]),
            view_type = view_element.data("view-type");

        views[view_type] = {
            view: view_element,
            selector: $(selector_item_query+"[data-view-type="+view_type+"]", element)
        };
    }

    switch_to_view(initial_selected_view);
}

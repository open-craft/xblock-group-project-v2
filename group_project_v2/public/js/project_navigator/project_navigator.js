function GroupProjectNavigatorBlock(runtime, element, initialization_args) {
    const initial_view = 'navigation';
    const selector_item_query = ".group-project-navigator-view-selector .view-selector-item";
    const activate_project_nav_view_event = 'group_project_v2.project_navigator.activate_view';

    var view_elements = $(".group-project-navigator-view", element),
        views = {},
        selected_view = initialization_args.selected_view;

    function switch_to_view(target_view) {
        var view_data = views[target_view];

        $(selector_item_query, element).removeClass('active');
        $(".group-project-navigator-view", element).hide();

        view_data.view.show();
        view_data.selector.addClass('active');
    }

    $(selector_item_query, element).click(function(e){
        var view_type = $(this).data("view-type");

        if (!views.hasOwnProperty(view_type)) {
            // Unknown view
            return;
        }

        e.preventDefault();
        switch_to_view(view_type);
    });

    $(".group-project-navigator-view-close").click(function(){
        switch_to_view(initial_view);
    });

    $(document).on(activate_project_nav_view_event, function(target, target_block_id) {
        var escaped_block_id = target_block_id.replace(/\//g, ";_");
        var target_block = $("[data-view-id='"+escaped_block_id+"']");
        if (target_block) {
            switch_to_view(target_block.data('view-type'));
        }
    });

    for (var i=0; i<=view_elements.length; i++) {
        var view_element = $(view_elements[i]),
            view_type = view_element.data("view-type");

        views[view_type] = {
            view: view_element,
            selector: $(selector_item_query+"[data-view-type="+view_type+"]", element)
        };
    }

    switch_to_view(selected_view);
}

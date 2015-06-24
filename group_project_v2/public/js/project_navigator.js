function GroupProjectNavigatorBlock(runtime, element) {
    const initial_view = 'navigation';
    const selector_item_query = ".group-project-navigator-view-selector .view-selector-item";

    var view_elements = $(".group-project-navigator-view", element),
        views = {};

    function switch_to_view(target_view) {
        var view_data = views[target_view];

        $(selector_item_query, element).removeClass('active');
        $(".group-project-navigator-view", element).hide();

        view_data.view.show();
        view_data.selector.addClass('active');
    }

    for (var i=0; i<=view_elements.length; i++) {
        var view_element = $(view_elements[i]),
            view_type = view_element.data("view-type");

        views[view_type] = {
            view: view_element,
            selector: $(selector_item_query+"[data-view-type="+view_type+"]", element)
        };
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

    switch_to_view(initial_view);
}

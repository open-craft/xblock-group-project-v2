function GroupProjectBlockDashboardDetailsView(runtime, element) {
    var selectors = {
        user_row_tpl: "tr.user-data-row[data-group-id=%GROUP_ID%]",
        group_row_tpl: "tr.group-data-row[data-group-id=%GROUP_ID%]",
        group_collapsed_icon: '.group-collapsed-icon',
        nav_icon: '.grade_group_icon',
        table: "table.activity-data",
        user_row: "tr.user-data-row",
        group_row: "tr.group-data-row",
        group_label: ".group-label"
    };

    var search_event = 'group_project_v2.details_view.search';
    var search_clear_event = 'group_project_v2.details_view.search_clear';
    var search_hit_class = 'search-hit';
    var icons = {
        collapsed: "fa-caret-right",
        expanded: "fa-caret-down"
    };
    var data_attributes = {
        collapsed: 'collapsed',
        group_id: 'group-id'
    };
    var collapsed_values = {
        collapsed: 'collapsed',
        expanded: 'expanded'
    };

    var search_selector = {
        email: "tr[data-email]",
        full_name: "tr[data-fullname]"
    };

    function format(template, replacements) {
        var temp_result = template;
        for (var key in replacements){
            if (!replacements.hasOwnProperty(key)) {
                continue;
            }
            temp_result = temp_result.replace('%'+key+'%', replacements[key]);
        }
        return temp_result
    }

    function expand_group(group_id) {
        var group_user_rows_selector = format(selectors.user_row_tpl, {'GROUP_ID': group_id});
        var group_row_selector = format(selectors.group_row_tpl, {'GROUP_ID': group_id});
        var group_label = $(group_row_selector, element).find(selectors.group_label);
        $(group_row_selector).data(data_attributes.collapsed, collapsed_values.expanded);
        $(group_user_rows_selector, element).show();
        $(selectors.group_collapsed_icon, group_label).removeClass(icons.collapsed).addClass(icons.expanded);
        $(selectors.nav_icon, group_label).show();
    }

    function collapse_group(group_id) {
        var group_user_rows_selector = format(selectors.user_row_tpl, {'GROUP_ID': group_id});
        var group_row_selector = format(selectors.group_row_tpl, {'GROUP_ID': group_id});
        var group_label = $(group_row_selector, element).find(selectors.group_label);
        $(group_row_selector).data(data_attributes.collapsed, collapsed_values.collapsed);
        $(group_user_rows_selector, element).hide();
        $(selectors.group_collapsed_icon, group_label).removeClass(icons.expanded).addClass(icons.collapsed);
        $(selectors.nav_icon, group_label).hide();
    }

    function collapse_all_groups() {
        var group_rows = $(selectors.table).find("tr.group-data-row");
        for (var i = 0; i< group_rows.length; i++) {
            var $row = $(group_rows[i]);
            var group_id = $row.data(data_attributes.group_id);
            collapse_group(group_id);
        }
    }

    function clear_search_highlighting() {
        $("table.activity-data", element).find(selectors.user_row).removeClass(search_hit_class);
    }

    $(document).ready(function () {
        $(selectors.group_label, element).click(function () {
            var $row = $(this).parents(selectors.group_row);
            var group_id = $row.data(data_attributes.group_id);
            var state = $row.data(data_attributes.collapsed);

            if (state === collapsed_values.expanded) {
                collapse_group(group_id);
            }
            else{
                expand_group(group_id);
            }
        });

        $(selectors.nav_icon, element).click(function(ev) {
            ev.stopPropagation();
        });

        $(document).on(search_event, function(target, search_criteria) {
            var search_regex = new RegExp(search_criteria, "i");
            collapse_all_groups();
            clear_search_highlighting();
            var search_hits = $(selectors.table)
                .find(search_selector.email)
                .add(search_selector.full_name)
                .filter(function() {
                    return (
                        search_regex.test($(this).data('email')) ||
                        search_regex.test($(this).data('fullname'))
                    );
                });

            search_hits.addClass(search_hit_class);

            for (var i=0; i<search_hits.length; i++) {
                var group_id = $(search_hits[i]).data(data_attributes.group_id);
                expand_group(group_id);
            }
        });

        $(document).on(search_clear_event, function() {
            clear_search_highlighting();
        })
    });
}

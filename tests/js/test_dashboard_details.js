/* global
    GroupProjectBlockDashboardDetailsConstants, GroupProjectBlockDashboardDetailsHelpers,
     GroupProjectBlockDashboardDetailsView
 */
var gp_constants = GroupProjectBlockDashboardDetailsConstants;
var gp_helpers = GroupProjectBlockDashboardDetailsHelpers;

describe('GroupProjectBlockDashboardDetailsView Tests', function(){
    'use strict';
    it("loads GroupProjectBlockDashboardDetailsView", function() {
        expect(GroupProjectBlockDashboardDetailsView).not.toBeUndefined();
        expect(GroupProjectBlockDashboardDetailsConstants).not.toBeUndefined();
    });

    function load_fixture(fixture, hold_ready) {
        var hold = hold_ready || true;
        var fixtures_loader = jasmine.getFixtures();
        fixtures_loader.fixturesPath = "base/tests/js/fixtures";
        fixtures_loader.load("generic.html");
        if (hold) {
            $.holdReady(false);
        }
    }

    function initialize_block() {
        var top_level_element = $(".xblock-dashboard_detail_view");
        GroupProjectBlockDashboardDetailsView({}, top_level_element);
    }

    function assert_group_collapsed(group_id) {
        var group_selector =  gp_helpers.format(gp_constants.selectors.group_row_tpl, {'GROUP_ID': group_id});
        var user_rows_selector = gp_helpers.format(gp_constants.selectors.user_row_tpl, {'GROUP_ID': group_id});
        var $group_row = $(group_selector);

        expect($(user_rows_selector)).toBeHidden();
        expect($(gp_constants.selectors.nav_icon, $group_row)).toBeHidden();
        expect($group_row.data(gp_constants.data_attributes.collapsed))
            .toBe(gp_constants.collapsed_values.collapsed);
        expect($(gp_constants.selectors.group_collapsed_icon, $group_row))
            .toHaveClass(gp_constants.icon_classes.collapsed);
    }

    function assert_group_expanded(group_id) {
        var group_selector =  gp_helpers.format(gp_constants.selectors.group_row_tpl, {'GROUP_ID': group_id});
        var user_rows_selector = gp_helpers.format(gp_constants.selectors.user_row_tpl, {'GROUP_ID': group_id});
        var $group_row = $(group_selector);

        expect($(user_rows_selector)).toBeVisible();
        expect($(gp_constants.selectors.nav_icon, $group_row)).toBeVisible();
        expect($group_row.data(gp_constants.data_attributes.collapsed))
            .toBe(gp_constants.collapsed_values.expanded);
        expect($(gp_constants.selectors.group_collapsed_icon, $group_row))
            .toHaveClass(gp_constants.icon_classes.expanded);
    }

    describe("Collapse/Expand Group", function() {
        beforeEach(function() {
            load_fixture("generic.html");
            initialize_block();
        });

        it("starts with groups collapsed", function() {
            expect($(gp_constants.selectors.user_row)).toBeHidden();
        });

        it("can expand group when clicked on collapsed group", function() {
            $.holdReady(true);
            var group_rows = $(gp_constants.selectors.group_row);
            for (var i = 0; i< group_rows.length; i++) {
                var $group_row = $(group_rows[i]);
                var group_id = $group_row.data(gp_constants.data_attributes.group_id);

                assert_group_collapsed(group_id); // precondition check

                $(gp_constants.selectors.group_label, $group_row).click();
                assert_group_expanded(group_id);
            }
        });

        it("can collapse group when clicked on expanded group", function() {
            $.holdReady(true);
            var group_rows = $(gp_constants.selectors.group_row);
            for (var i = 0; i< group_rows.length; i++) {
                var group_row = group_rows[i];
                var group_id = $(group_row).data(gp_constants.data_attributes.group_id);

                $(gp_constants.selectors.group_label, group_row).click();
                assert_group_expanded(group_id); // precondition check

                $(gp_constants.selectors.group_label, group_row).click();
                assert_group_collapsed(group_id);
            }
        });
    });

    describe("User search", function() {
        beforeEach(function() {
            load_fixture("generic.html");
            initialize_block();
        });

        it("can search by username", function() {
            $.holdReady(true);
            var search_criteria = 'derek_email';
            var $search_hit = $(gp_constants.selectors.user_row).filter("[data-email='derek_email@example.com']");

            // precondition
            expect($search_hit).not.toHaveClass(gp_constants.search_hit_class);

            $(document).trigger(gp_constants.events.search, search_criteria);

            expect($search_hit).toHaveClass(gp_constants.search_hit_class);
        });

        it("can search by email", function() {
            $.holdReady(true);
            var search_criteria = 'derek';
            var $search_hit = $(gp_constants.selectors.user_row).filter("[data-fullname='Derek Doe']");

            // precondition
            expect($search_hit).not.toHaveClass(gp_constants.search_hit_class);

            $(document).trigger(gp_constants.events.search, search_criteria);

            expect($search_hit).toHaveClass(gp_constants.search_hit_class);
        });

        it("expands search hit group", function() {
            $.holdReady(true);
            var search_criteria = 'bob';
            var $search_hit = $(gp_constants.selectors.user_row).filter("[data-fullname='Bob Doe']");
            var search_hit_group_id = $search_hit.data(gp_constants.data_attributes.group_id);


            // precondition
            expect($search_hit).not.toHaveClass(gp_constants.search_hit_class);
            expect($search_hit).toBeHidden();
            assert_group_collapsed(search_hit_group_id);

            $(document).trigger(gp_constants.events.search, search_criteria);

            expect($search_hit).toHaveClass(gp_constants.search_hit_class);
            expect($search_hit).toBeVisible();
            assert_group_expanded(search_hit_group_id);
        });

        it("clears old search results when new search is performed", function() {
            $.holdReady(true);
            var search_criteria = 'bob';
            var $search_hit = $(gp_constants.selectors.user_row).filter("[data-fullname='Bob Doe']");
            $(document).trigger(gp_constants.events.search, search_criteria);
            expect($search_hit).toBeVisible();
            expect($search_hit).toHaveClass(gp_constants.search_hit_class);

            search_criteria = 'alice';
            var $new_search_hit = $(gp_constants.selectors.user_row).filter("[data-fullname='Alice Doe']");
            $(document).trigger(gp_constants.events.search, search_criteria);

            expect($search_hit).not.toHaveClass(gp_constants.search_hit_class);
            expect($new_search_hit).toBeVisible();
            expect($new_search_hit).toHaveClass(gp_constants.search_hit_class);
        });

        it ("collapses expanded groups with no search hits", function() {
            $.holdReady(true);

            var group_row, group_id, i;

            var search_criteria = 'bob';
            var $search_hit = $(gp_constants.selectors.user_row).filter("[data-fullname='Bob Doe']");
            var search_hit_group_id = $search_hit.data(gp_constants.data_attributes.group_id);

            // let's just expand all of them
            var group_rows = $(gp_constants.selectors.group_row);
            for (i = 0; i< group_rows.length; i++) {
                group_row = group_rows[i];
                group_id = $(group_row).data(gp_constants.data_attributes.group_id);

                $(gp_constants.selectors.group_label, group_row).click();
                assert_group_expanded(group_id); // precondition check
            }

            $(document).trigger(gp_constants.events.search, search_criteria);

            for (i = 0; i< group_rows.length; i++) {
                group_row = group_rows[i];
                group_id = $(group_row).data(gp_constants.data_attributes.group_id);

                var assertion = (group_id !== search_hit_group_id) ? assert_group_collapsed : assert_group_expanded;
                assertion(group_id);
            }
        });

        it("when clear_search event received, clears search highlighting", function() {
            $.holdReady(true);
            var search_criteria = 'example.com';
            var $search_hits = $(gp_constants.selectors.user_row).filter("[data-email*='example.com']"); // all rows

            // precondition
            $(document).trigger(gp_constants.events.search, search_criteria);
            expect($search_hits).toHaveClass(gp_constants.search_hit_class);

            $(document).trigger(gp_constants.events.clear_search);
            expect($search_hits).not.toHaveClass(gp_constants.search_hit_class);
        });
    });
});

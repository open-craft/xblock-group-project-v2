/* global ReviewSubjectSelectorXBlock, ReviewSubjectSelectorConstants, GroupProjectCommon, TestUtils */
var ReviewStatus = {
    NOT_STARTED: 'not_started',
    INCOMPLETE: 'incomplete',
    COMPLETED: 'completed'
};

describe("Review subject selector", function() {
    'use strict';
    it("loads ReviewSubjectSelectorXBlock", function() {
        expect(ReviewSubjectSelectorXBlock).not.toBeUndefined();
    });

    function common_features_test_suite(suite_prefix, html_fixture) {
        function get_status(review_subject_id) {
            var status_icon = $(".review_subject[data-id="+review_subject_id+"]")
                .children('.'+ReviewSubjectSelectorConstants.status_icon_class);
            var css_classes = status_icon.attr('class').split(/\s+/);
            var non_fixed_classes = css_classes.filter(function(element, _index, _array) {
                /* jshint unused:false */
                return (element !== ReviewSubjectSelectorConstants.status_icon_class) && (!element.startsWith('fa'));
            });
            return non_fixed_classes ? non_fixed_classes[0] : ReviewStatus.NOT_STARTED;
        }

        describe(suite_prefix, function(){
            var handler_urls = {get_statuses: '/i/am/url/for/get_statuses/handler'};
            var mock_runtime = {
                handlerUrl: function(element, handler) {
                    return handler_urls[handler];
                }
            };

            beforeEach(function() {
                TestUtils.load_fixture(html_fixture + ".html");
            });

            it('loads state after initialization', function(){
                spyOn($, "ajax").and.callFake(function(){
                    var def = $.Deferred();
                    def.resolve({1: ReviewStatus.NOT_STARTED, 2: ReviewStatus.INCOMPLETE});
                    return def;
                });

                var top_element = $(".xblock");
                ReviewSubjectSelectorXBlock(mock_runtime, top_element);

                var ajax_call = $.ajax.calls.mostRecent();
                expect(ajax_call).toBeDefined();
                var ajax_args = ajax_call.args[0];
                expect(ajax_args.url).toBe(handler_urls.get_statuses);
                expect(get_status(1)).toBe(ReviewStatus.NOT_STARTED);
                expect(get_status(2)).toBe(ReviewStatus.INCOMPLETE);
            });

            it('refreshes state when event is fired', function(){
                var statuses = {1: ReviewStatus.NOT_STARTED, 2: ReviewStatus.INCOMPLETE};
                spyOn($, "ajax").and.callFake(function(){
                    var def = $.Deferred();
                    def.resolve(statuses);  // closing on external variable - this is intentional
                    return def;
                });

                var top_element = $(".xblock");
                ReviewSubjectSelectorXBlock(mock_runtime, top_element);

                statuses[1] = ReviewStatus.COMPLETED;
                statuses[2] = ReviewStatus.COMPLETED;

                $(document).trigger(GroupProjectCommon.Review.events.refresh_status);

                var ajax_call = $.ajax.calls.mostRecent();
                expect(ajax_call).toBeDefined();
                var ajax_args = ajax_call.args[0];
                expect(ajax_args.url).toBe(handler_urls.get_statuses);
                expect(get_status(1)).toBe(ReviewStatus.COMPLETED);
                expect(get_status(2)).toBe(ReviewStatus.COMPLETED);
            });
        });
    }

    common_features_test_suite("Peer Selector", "peer_selector");
    common_features_test_suite("Group Selector", "group_selector");
});

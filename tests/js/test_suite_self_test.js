/* global GroupProjectBlock, GroupProjectCommon, GroupProjectNavigatorBlock, TestUtils */
/* Contains assertions about the suite itself - mostly if required components are available */
describe("Suite self-test", function() {
    'use strict';

    function load_test(item) {
        var name = item.toString();
        it("loads "+name, function(){
           expect(item).not.toBeUndefined();
        });
    }

    /* XBlocks */
    var loads = [GroupProjectBlock, GroupProjectCommon, GroupProjectNavigatorBlock];

    loads.forEach(load_test);

    /* Test utils */
    var test_utils = [TestUtils];

    test_utils.forEach(load_test);
});

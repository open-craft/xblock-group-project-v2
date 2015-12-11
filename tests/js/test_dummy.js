/* global GroupProjectBlock, GroupProjectNavigatorBlock */
describe("Suite self-test", function() {
    'use strict';
    it("loads GroupProjectBlock", function() {
        expect(GroupProjectBlock).not.toBeUndefined();
    });

    it("loads GroupProjectNavigatorBlock", function() {
        expect(GroupProjectNavigatorBlock).not.toBeUndefined();
    });
});

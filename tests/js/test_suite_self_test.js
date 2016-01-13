/* global GroupProjectBlock, GroupProjectNavigatorBlock, ProjectTeamXBlock */
/* Contains assertions about the suite itself - mostly if required components are available */
describe("Suite self-test", function() {
    'use strict';
    var loads = [GroupProjectBlock, GroupProjectNavigatorBlock, ProjectTeamXBlock];

    loads.forEach(function(item) {
        var name = item.toString();
        it("loads "+name, function(){
           expect(item).not.toBeUndefined();
        });
    });
});

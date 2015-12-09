describe('GroupProjectBlockDashboardDetailsView Tests', function(){
    it("loads GroupProjectBlockDashboardDetailsView", function() {
        expect(GroupProjectBlockDashboardDetailsView).not.toBeUndefined();
    });

    beforeEach(function() {
        debugger;
        var fixtures_loader = jasmine.getFixtures();
        fixtures_loader.fixturesPath = "base/tests/js/fixtures";
        fixtures_loader.load("generic.html");
    });
});
/* exported TestUtils */
function TestUtilsConstructor() {
    var fixtures_loader = jasmine.getFixtures();
    fixtures_loader.fixturesPath = "base/tests/js/fixtures";

    return {
        load_fixture: function(fixture, hold_ready) {
            var hold = hold_ready || true;
            fixtures_loader.load(fixture);
            if (hold) {
                $.holdReady(false);
            }
        },
        parseUrlEncoded: function(urlencoded) {
            return JSON.parse('{"' +
                decodeURIComponent(urlencoded).replace(/"/g, '\\"').replace(/&/g, '","').replace(/=/g,'":"') + '"}'
            );
        }
    }
}

var TestUtils = TestUtilsConstructor();
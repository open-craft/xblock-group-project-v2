/* global ProjectTeamXBlock, ProjectTeamXBlockConstants, TestUtils */
/* Contains assertions about the suite itself - mostly if required components are available */
var FixtureConstants = {
    teammates: {
        Alice: {
            name: "Alice Doe",
            email: "Alice@example.com"
        },
        Derek: {
            name: "Derek Doe",
            email: "Derek@example.com"
        }
    },
    urls: {
        email_teammate: "/courses/McKinsey/GP2/T1/group_member_email/20",
        email_group: "/courses/McKinsey/GP2/T1/group_email/20"
    }
};

describe("ProjectTeamXBlock", function() {
    'use strict';
    'use strict';
    it("loads ProjectTeamXBlock", function() {
        expect(ProjectTeamXBlock).not.toBeUndefined();
    });

    beforeEach(function() {
        TestUtils.load_fixture("project_team.html");
        var project_team_top_level_element = $(".xblock-student_view-gp-v2-project-team");
        ProjectTeamXBlock({}, project_team_top_level_element);
        $.cookie = function(){};
        spyOn($, 'cookie').and.returnValue("Iamcsrftoken");
    });

    describe("Email teammate", function() {
        function get_email_teammate_popup() {
            return $(ProjectTeamXBlockConstants.teammate.modal);
        }

        function get_teammate_email($teammate_popup) {
            return $teammate_popup.find("form input.member-email").val();
        }

        it("opens an email popup dialog when clicked on 'Email' teammate", function(){
            var links = $(ProjectTeamXBlockConstants.teammate.anchor);
            links.each(function(idx, link) {
                var expected_email = $(link).data("email");
                $(link).click();
                var email_teammate_popup = get_email_teammate_popup();
                expect(email_teammate_popup).toBeVisible();
                expect(get_teammate_email(email_teammate_popup)).toEqual(expected_email);
            });
        });

        describe("popup", function(){
            function open_popup(email) {
                var link_selector = (email) ?
                    ".group-project-team-member-email a[data-email='"+email+"']" :
                    ProjectTeamXBlockConstants.teammate.anchor;
                $(link_selector).click();
                return get_email_teammate_popup();
            }

            it("can be closed", function(){
                var $popup = open_popup();
                expect($popup).toBeVisible();
                $popup.find(".close-box").click();
                expect($popup).toBeHidden();
            });

            it("does not clear textarea on close", function(){
                var text = "Quick brown fox jumped over the lazy dog";
                var $popup = open_popup();
                expect($popup).toBeVisible();
                var textarea = $popup.find("textarea[name='member_message']");
                textarea.val(text);
                expect(textarea.val()).toEqual(text);
                $popup.find(".close-box").click();
                expect(textarea.val()).toEqual(text);
                expect($popup).toBeHidden();
            });

            var submit_suite_data = {
                "Test1": {
                    text: "test", email: FixtureConstants.teammates.Alice.email, message: "Message1"
                },
                "Test2": {
                    text: "other_test", email: FixtureConstants.teammates.Derek.email, message: "Message2"
                }
            };

            function test_email_send(testName, parameters) {
                it("sends ajax when submitted - case "+testName, function() {
                    spyOn($, "ajax").and.callFake(function(){
                        var deferred = $.Deferred();
                        deferred.resolve({message: parameters.message});
                        return deferred;
                    });
                    var $popup = open_popup(parameters.email);
                    expect($popup).toBeVisible();
                    var textarea = $popup.find("textarea[name='member_message']");
                    textarea.val(parameters.text);
                    $popup.find("form").submit();
                    var ajax_call = $.ajax.calls.mostRecent();
                    expect(ajax_call).toBeDefined();
                    var ajax_args = ajax_call.args[0];
                    var data = TestUtils.parseUrlEncoded(ajax_args['data']);
                    expect(ajax_args['url']).toEqual(FixtureConstants.urls.email_teammate);
                    expect(data["member-email"]).toEqual(parameters.email);
                    expect(data["member_message"]).toEqual(parameters.text);
                    expect(textarea.val()).toEqual(''); // clears textarea on successful submission
                });
            }

            for (var testName in submit_suite_data) {
                if (submit_suite_data.hasOwnProperty(testName)) {
                    var parameters = submit_suite_data[testName];
                    test_email_send(testName, parameters);
                }
            }
        });
    });

    describe("Email teammate", function() {
        function get_email_group_popup() {
            return $(ProjectTeamXBlockConstants.group.modal);
        }

        it("opens an email popup dialog when clicked on 'Email your entire team'", function(){
            var link = $(ProjectTeamXBlockConstants.group.anchor);
            $(link).click();
            var email_popup = get_email_group_popup();
            expect(email_popup).toBeVisible();
        });

        describe("popup", function(){
            function open_popup() {
                $(ProjectTeamXBlockConstants.group.anchor).click();
                return get_email_group_popup();
            }

            it("can be closed", function(){
                var $popup = open_popup();
                expect($popup).toBeVisible();
                $popup.find(".close-box").click();
                expect($popup).toBeHidden();
            });

            it("does not clear textarea on close", function(){
                var text = "Quick brown fox jumped over the lazy dog";
                var $popup = open_popup();
                expect($popup).toBeVisible();
                var textarea = $popup.find("textarea[name='group_message']");
                textarea.val(text);
                expect(textarea.val()).toEqual(text);
                $popup.find(".close-box").click();
                expect(textarea.val()).toEqual(text);
                expect($popup).toBeHidden();
            });

            var submit_suite_data = {
                "Test1": {
                    text: "test", message: "Message1"
                },
                "Test2": {
                    text: "other_test", message: "Message2"
                }
            };

            function test_email_send(testName, parameters) {
                it("sends ajax when submitted - case "+testName, function() {
                    spyOn($, "ajax").and.callFake(function(){
                        var deferred = $.Deferred();
                        deferred.resolve({message: parameters.message});
                        return deferred;
                    });
                    var $popup = open_popup(parameters.email);
                    expect($popup).toBeVisible();
                    var textarea = $popup.find("textarea[name='group_message']");
                    textarea.val(parameters.text);
                    $popup.find("form").submit();
                    var ajax_call = $.ajax.calls.mostRecent();
                    expect(ajax_call).toBeDefined();
                    var ajax_args = ajax_call.args[0];
                    var data = TestUtils.parseUrlEncoded(ajax_args['data']);
                    expect(ajax_args['url']).toEqual(FixtureConstants.urls.email_group);
                    expect(data["group_message"]).toEqual(parameters.text);
                    expect(textarea.val()).toEqual(''); // clears textarea on successful submission
                });
            }

            for (var testName in submit_suite_data) {
                if (submit_suite_data.hasOwnProperty(testName)) {
                    var parameters = submit_suite_data[testName];
                    test_email_send(testName, parameters);
                }
            }
        });
    });
});

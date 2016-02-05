/* exported ReviewSubjectSelectorXBlock */
function ReviewSubjectSelectorXBlock(runtime, element) {
    "use strict";
    // Set up gettext in case it isn't available in the client runtime:
    if (typeof gettext === "undefined") {
        window.gettext = function gettext_stub(string) { return string; };
    }

    var ERROR_REFRESHING_STATUSES = gettext("Error refreshing statuses");

    var refresh_statuses_event = "group_project_v2.review.refresh_status";
    var get_statuses_endpoint = runtime.handlerUrl(element, "get_statuses");
    var status_icon_class = "group-project-review-state";

    var group_project_dom = $(element).parents(".group-project-xblock-wrapper");
    var message_box = $(".message", group_project_dom);

    function show_message(msg, title, title_css_class) {
        message_box.find('.message_text').html(msg);
        message_box.find('.message_title').html(title);
        if (title_css_class) {
            message_box.find('.message_title').addClass(title_css_class);
        }
        message_box.show();
    }

    function resetCssClasses() {
        $("."+status_icon_class, element).removeClass().addClass(status_icon_class);
    }

    function displaySpinners() {
        $("."+status_icon_class, element).addClass('fa-spin fa-spinner');
    }

    function setStatus(review_subject_id, status_css_class) {
        var $review_subject_wrapper = $(".review_subject[data-id="+review_subject_id+"]");
        $("."+status_icon_class, $review_subject_wrapper).removeClass('fa-spin fa-spinner').addClass(status_css_class);
    }

    $(document).on(refresh_statuses_event, function() {
        resetCssClasses();
        displaySpinners();
        $.ajax({
            dataType: 'json', url: get_statuses_endpoint,  method: 'GET'
        }).done(function(data){
            for (var review_subject_id in data) {
                if (!data.hasOwnProperty(review_subject_id)) {
                    continue;
                }

                setStatus(review_subject_id, data[review_subject_id]);
            }
        }).fail(function() {
            show_message(ERROR_REFRESHING_STATUSES);
        });
    });

    $(document).trigger(refresh_statuses_event);
}
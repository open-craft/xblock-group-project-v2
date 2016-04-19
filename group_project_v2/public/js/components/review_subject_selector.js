/* global GroupProjectCommon */
/* exported ReviewSubjectSelectorXBlock, ReviewSubjectSelectorConstants */
var ReviewSubjectSelectorConstants = {
    status_icon_class: "group-project-review-state"
};

function ReviewSubjectSelectorXBlock(runtime, element) {
    "use strict";
    var ERROR_REFRESHING_STATUSES = GroupProjectCommon.gettext("Error refreshing statuses");

    var get_statuses_endpoint = runtime.handlerUrl(element, "get_statuses");
    var status_icon_class = ReviewSubjectSelectorConstants.status_icon_class;

    function show_message(msg, title, title_css_class) {
        GroupProjectCommon.Messages.show_message(msg, title, title_css_class);
    }

    function resetCssClasses() {
        $("."+status_icon_class, element).removeClass().addClass(status_icon_class).addClass('fa');
    }

    function displaySpinners() {
        $("."+status_icon_class, element).addClass('fa-spin fa-spinner');
    }

    function setStatus(review_subject_id, status_css_class) {
        var $review_subject_wrapper = $(".review_subject[data-id="+review_subject_id+"]");
        $("."+status_icon_class, $review_subject_wrapper).removeClass('fa-spin fa-spinner').addClass(status_css_class);
    }

    $(document).on(GroupProjectCommon.Review.events.refresh_status, function() {
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

    $(document).trigger(GroupProjectCommon.Review.events.refresh_status);
}

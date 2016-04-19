/* global GroupProjectCommon */
/* exported GroupProjectNavigatorAskTAView */
function GroupProjectNavigatorAskTAView(runtime, element) {
    "use strict";
    var view_identifier = 'ask-ta';

    var form = $(".contact-ta-form", element),
        textarea = $("textarea", form);

    $(textarea).on('keyup', function () {
        if ($(this).val() === '') {
            $(this).parent('form').find('input[type=submit]').prop('disabled', 'disabled');
        }
        else {
            $(this).parent('form').find('input[type=submit]').prop('disabled', false);
        }
    });

    $(form).on('submit', function(e){
        e.preventDefault();
        $(".csrfmiddlewaretoken", $(this)).val($.cookie('apros_csrftoken'));
        var data = $(this).serialize();
        $.ajax(
            {
                url: $(this).attr('action'),
                method: 'POST',
                data: data
            }).done(function (data) {
                var modal = $('#generalModal');
                modal.find('.title').html('Notification');
                modal.find('.description').html(data.message);
                setTimeout(function () {
                    modal.foundation('reveal', 'open');
                }, 350);
            });
    });

    $(document).on(GroupProjectCommon.ProjectNavigator.events.switch_view, function(target, event_data) {
        if (event_data.old_view === view_identifier) {
            $(textarea).val('');
        }
    });
}

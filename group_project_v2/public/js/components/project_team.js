function ProjectTeamXBlock(runtime, element) {
    const email_memeber_modal_selector = ".group-project-team-email-member-modal";
    const email_group_modal_selector = ".group-project-team-email-group-modal";

    var group_project_dom = $(element).parents(".group-project-xblock-wrapper");
    var message_box = $(".message", group_project_dom);

    function show_message(msg, title) {
        message_box.find('.message_text').html(msg);
        message_box.find('.message_title').html(title);
        message_box.show();
    }

    function showModal(target_modal){
        $(target_modal, element).show();
    }

    $(".group-project-team-email-group", element).click(function(ev){
        ev.preventDefault();
        showModal(email_group_modal_selector);
    });

    $(".group-project-team-member-email a[data-email]", element).click(function(ev){
        ev.preventDefault();
        var form = $(email_memeber_modal_selector, element).find('form'),
            member_email = $(this).data('email');
        $(".member-email", form).val(member_email);
        showModal(email_memeber_modal_selector);
    });

    var modal_dialogs = $(email_memeber_modal_selector, element).add(email_group_modal_selector, element);

    modal_dialogs.find('form').submit(function(ev){
        ev.preventDefault();
        $(".csrfmiddlewaretoken", $(this)).val($.cookie('apros_csrftoken'));
        var data = $(this).serialize();
        $.ajax({
            url: $(this).attr('action'),
            method: 'POST',
            data: data
        }).done(function (data) {
            show_message(data.message, 'Notification');
        });
    });

    modal_dialogs.find(".button, .close-box").click(function(){
        $(this).parents(".group-project-team-email-dialog").hide();
    });

    modal_dialogs.find('textarea').on('keyup', function () {
        if ($(this).val() == '') {
            $(this).parent('form').find('input[type=submit]').prop('disabled', 'disabled');
        }
        else {
            $(this).parent('form').find('input[type=submit]').prop('disabled', false);
        }
    });
}

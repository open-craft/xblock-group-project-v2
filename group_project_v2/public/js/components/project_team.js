/* exported ProjectTeamXBlock, ProjectTeamXBlockConstants */
var ProjectTeamXBlockConstants = {
    teammate: {
        modal: ".group-project-team-email-member-modal",
        anchor: ".group-project-team-member-email a[data-email]"
    },
    group: {
        modal: ".group-project-team-email-group-modal",
        anchor: ".group-project-team-email-group"
    }
};

function ProjectTeamXBlock(runtime, element) {
    "use strict";
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

    function showModal(target_modal){
        $(target_modal, group_project_dom).show();
    }

    function clearText(target_modal) {
        $(target_modal, group_project_dom).find('textarea').val('');
    }

    $(ProjectTeamXBlockConstants.group.anchor, element).click(function(ev){
        ev.preventDefault();
        showModal(ProjectTeamXBlockConstants.group.modal);
    });

    $(ProjectTeamXBlockConstants.teammate.anchor, element).click(function(ev){
        ev.preventDefault();
        var form = $(ProjectTeamXBlockConstants.teammate.modal, group_project_dom).find('form'),
            member_email = $(this).data('email');
        $(".member-email", form).val(member_email);
        showModal(ProjectTeamXBlockConstants.teammate.modal);
    });

    var modal_dialogs = $(ProjectTeamXBlockConstants.teammate.modal, group_project_dom)
        .add(ProjectTeamXBlockConstants.group.modal, group_project_dom);

    modal_dialogs.find('form').submit(function(ev){
        var $this = this;
        ev.preventDefault();
        $(".csrfmiddlewaretoken", $this).val($.cookie('apros_csrftoken'));
        var data = $(this).serialize();
        $.ajax({
            url: $(this).attr('action'),
            method: 'POST',
            data: data
        }).done(function (data) {
            show_message(data.message, '');
            clearText($this);
        }).fail(function (data) {
            show_message(data.message, 'Error', 'error');
        });
    });

    modal_dialogs.find(".button, .close-box, .modal-bg").click(function(){
        $(this).parents(".group-project-team-email-dialog").hide();
    });

    modal_dialogs.find('textarea').on('keyup', function () {
        if ($(this).val() === '') {
            $(this).parent('form').find('input[type=submit]').prop('disabled', 'disabled');
        }
        else {
            $(this).parent('form').find('input[type=submit]').prop('disabled', false);
        }
    });
}

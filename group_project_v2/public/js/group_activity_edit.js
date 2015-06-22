function GroupActivityEditBlock(runtime, element) {
    var xmlEditorTextarea = $('.block-xml-editor', element),
        xmlEditor = CodeMirror.fromTextArea(xmlEditorTextarea[0], {mode: 'xml', lineWrapping: true});

    $(element).find('.save-button').bind('click', function () {
        var data = {
            'display_name': $(element).find('.edit-display-name').val(),
            'max_score': parseFloat($('.edit-max-score', element).val()),
            'group_reviews_required_count': parseInt($('.edit-ta-graded', element).is(':checked') ? 0 : $('.edit-group-review-count', element).val()),
            'user_review_count': parseInt($('.edit-ta-graded', element).is(':checked') ? 0 : $('.edit-user-review-count', element).val()),
            'data': xmlEditor.getValue()
        };

        $('.xblock-editor-error-message', element).html();
        $('.xblock-editor-error-message', element).css('display', 'none');
        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
        $.post(handlerUrl, JSON.stringify(data)).done(function (response) {
            if (response.result === 'success') {
                window.location.reload(false);
            } else {
                $('.xblock-editor-error-message', element).html('Error: ' + response.message);
                $('.xblock-editor-error-message', element).css('display', 'block');
            }
        });
    });

    $(element).find('.cancel-button').bind('click', function () {
        runtime.notify('cancel', {});
    });

    var hide_show_for_ta = function () {
        $('.not-ta-graded', element).toggle(!$('.edit-ta-graded', element).is(':checked'));
    };

    $('.edit-ta-graded', element).on('change', function () {
        hide_show_for_ta();
    });

    $(function () {
        hide_show_for_ta();
    });
}

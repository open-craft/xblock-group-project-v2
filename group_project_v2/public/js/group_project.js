function GroupProjectBlock(runtime, element) {
    var message_box = $('.message', element).appendTo($(document.body));
    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
    });
}

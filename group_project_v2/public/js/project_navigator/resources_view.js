function GroupProjectNavigatorResourcesView(runtime, element) {
    const ooyala_player_target_element_id = 'group-project-resources-view-ooyala-player';

    var modal = $('.player-modal', element),
        player = $('.player-wrapper', modal),
        modal_bg = $(".player-modal-bg");

    function showPlayer() {
        modal.show();
        modal_bg.show();
    }

    function hidePlayer() {
        modal.hide();
        modal_bg.hide();
    }

    $('a[data-video]', element).on('click', function (e) {
        e.preventDefault();
        var video = $(e.currentTarget).data('video');

        player.append($('<div id="'+ooyala_player_target_element_id+'"/>'));

        var ooyala = null;
        if (typeof OO === 'undefined') return;
        if ($('body').hasClass('ie8')) {
            ooyala = OO.Player.create(ooyala_player_target_element_id, video, {width: '740px', height: '425px'});
        } else {
            ooyala = OO.Player.create(ooyala_player_target_element_id, video, {width: '100%', height: '100%'});
        }
        modal.data('ooyala', ooyala);
        showPlayer();
    });

    $('.close-reveal-modal', element).add('.player-modal-bg', element).on('click', function () {
        var ooyala = modal.data('ooyala');
        if (ooyala) {
            ooyala.destroy();
            modal.removeData('ooyala');
        }
        player.empty();
        hidePlayer();
    });
}

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

    $('a[data-video-id]', element).on('click', function (e) {
        e.preventDefault();
        var video = $(e.currentTarget).data('video-id');

        player.append($('<div id="'+ooyala_player_target_element_id+'"/>'));

        if (typeof OO === 'undefined') return;
        // TODO: manually using ooyala - replace with Ooyala player XBlock when it's autostart setting is fixed
        // and play-stop-destroy events are exposed.
        var parameters = {width: '100%', height: '100%', autoplay: true};

        var  ooyala = OO.Player.create(ooyala_player_target_element_id, video, parameters);
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

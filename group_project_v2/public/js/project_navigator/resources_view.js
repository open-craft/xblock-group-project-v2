/* global OO */
/* exported GroupProjectNavigatorResourcesView */
function GroupProjectNavigatorResourcesView(runtime, element) {
    "use strict";
    var ooyala_player_target_element_id = 'group-project-resources-view-ooyala-player';

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
        var videoId = $(e.currentTarget).data('video-id');
        var playerType = $(e.currentTarget).data('player-type');
        
        // kickoff player according to video type
        if (playerType === 'brightcove'){
            var elemId = $('.video-js').attr('id');
            videojs.getPlayer(elemId).ready(function () {
                this.play();
            });
            showPlayer();
        }else if(playerType === 'ooyala'){
            if (typeof OO === 'undefined') 
                return;
        
            player.append($('<div id="'+ooyala_player_target_element_id+'"/>'));
            var parameters = {width: '100%', height: '100%', autoplay: true};
            var video = OO.Player.create(ooyala_player_target_element_id, videoId, parameters);
            modal.data('video', video);
            showPlayer();
        }else{
            return;
        }
    });

    $('.close-reveal-modal', element).add('.player-modal-bg', element).on('click', function () {
        var video = modal.data('video');
        var bcVideo = $('.video-js', modal);

        if (video) {
            video.destroy();
            player.empty();
            modal.removeData('video');
        }

        // stop any BC video 
        if(bcVideo.length){
            videojs.getPlayer(bcVideo.attr('id')).ready(function () {
                this.pause();
                // seek to zero as no stop method is available 
                // in HTML5 video API
                this.currentTime(0);
            });
        }
        
        hidePlayer();
    });
}

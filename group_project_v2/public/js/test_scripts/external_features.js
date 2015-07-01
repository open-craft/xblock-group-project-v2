function external_navigation() {
    $(".group-project-stage a").click(function(e){
        e.preventDefault();
        var stage_id = $(this).data('stage-id');
        $(document).trigger('select_stage', stage_id);
    })
}

function initialization() {

}

$(".xblock_asides-v1").remove(); // not related to initialization, but those asides all over the place irritate me

initialization();
external_navigation();
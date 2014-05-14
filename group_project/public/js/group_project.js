$(function(){
  var step_ids = ['overview','upload','review','grade'];
  var step_map = {};
  for(var i = 0; i < step_ids.length; ++i){
    step_map[step_ids[i]] = {
      "prev": (i == 0 ) ? null : step_ids[i-1],
      "next": (i == (step_ids.length-1)) ? null : step_ids[i+1]
    };
  }

  $('.revealer').on('click', function(ev){
    // Hide show correct content
    var selected_step = $(this).attr('id');
    $('.revealer').removeClass('selected');
    $(this).addClass('selected');

    $('.activity_section').hide();
    $('#activity_' + selected_step).show();

    // Update step makers
    var step_pn = step_map[selected_step];
    $('#prev, #next').off('click').attr('disabled', 'disabled');
    if(step_pn["prev"]){
      $('#prev').on('click', function(){$("#" + step_pn["prev"]).click();}).removeAttr('disabled');
    }
    if(step_pn["next"]){
      $('#next').on('click', function(){$("#" + step_pn["next"]).click();}).removeAttr('disabled');
    }

    ev.preventDefault();
  });

  $('#overview').click();
});
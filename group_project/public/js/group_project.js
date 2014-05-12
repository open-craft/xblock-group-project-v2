$(function(){
  $('.revealer').on('click', function(){
    $('.activity_section').hide();
    $('#activity_' + $(this).attr('id')).show();
  })
});
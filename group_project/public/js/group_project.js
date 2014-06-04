function GroupProjectBlock(runtime, element) {

  $('form').on('submit', function(ev){
    ev.preventDefault();
    var form = $(this);

    form.find(':submit').prop('disabled', true);
    items = form.serializeArray();
    data = {}
    $.each(items, function(i,v){
      data[v.name] = v.value;
    });

    $.ajax({
      type: form.attr('method'),
      url: runtime.handlerUrl(element, form.attr('action')),
      data: JSON.stringify(data),
      success: function(data){
        var msg = 'Thanks for your feedback!';
        if(data['msg']){
          msg = data['msg'];
        }
        alert(msg);
      },
      error: function(data){
        alert('Sorry, there was an error saving your feedback');
      },
      complete: function(data){
        form.find(':submit').prop('disabled', false);
      }
    });

    return false;
  });

  var peers = JSON.parse($('#peer_group').html());
  var peer_node = function(peer){
    var pn = $('<a class="select_peer" />');
    var pi = $('<img class="avatar" />');
    pi.attr('src', peer.img);
    pn.attr('title', peer.name);
    pn.data('id', peer.id);
    pn.append(pi);

    return pn;
  }

  for(var i=0; i < peers.length; ++i){
    $('#peers').append(peer_node(peers[i]));
  }

  var groups = JSON.parse($('#assess_groups').html());
  var group_node = function(group){
    var gn = $('<a class="select_group" />');
    var gi = $('<img class="avatar" />');
    gi.attr('src', group.img);
    gn.data('id', group.id);
    gn.append(gi);

    return gn;
  }

  for(var i=0; i < groups.length; ++i){
    $('#other_groups').append(group_node(groups[i]));
  }


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
    $('#prev, #next').off('click').removeAttr('href');
    if(step_pn["prev"]){
      $('#prev').on('click', function(){$("#" + step_pn["prev"]).click();}).attr('href', '#');
    }
    if(step_pn["next"]){
      $('#next').on('click', function(){$("#" + step_pn["next"]).click();}).attr('href', '#');
    }

    ev.preventDefault();
  });

  $('.view_feedback').on('click', function(ev){
    $('.feedback_sections').hide();
    $('.view_feedback').removeClass('selected');
    var showid = $(this).data('showid');
    $('#' + showid).show();
    $(this).addClass('selected');

    ev.preventDefault();
  });

  $('.select_peer').on('click', function(ev){
    $('.select_peer,.select_group').removeClass('selected');
    $(this).addClass('selected');
    $('#other_group_review').hide();
    $('#peer_review').show();
    $('#peer_id').attr('value', $(this).data('id'));
  });

  $('.select_group').on('click', function(ev){
    $('.select_peer,.select_group').removeClass('selected');
    $(this).addClass('selected');
    $('#other_group_review').show();
    $('#peer_review').hide();
    $('#group_id').attr('value', $(this).data('id'));
  });

  $('#overview').click();
  $('.view_feedback:first').click();

}
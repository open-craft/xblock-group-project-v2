function GroupProjectBlock(runtime, element) {

  var mean = function(value_array){
    var sum = 0;
    var count = value_array.length;
    if(count < 1){
      return null;
    }

    for(var i=0; i<count; ++i){
      sum += parseFloat(value_array[i]);
    }

    return sum / count;
  }

  var load_data_into_form = function (form_id, data_for_form){
    var $form = $("." + form_id, element);
    $form.find('.answer').val(null);
    for(data_item in data_for_form){
      // NOTE: use of ids specified by designer here
      var $form_item = $form.find("#" + data_item);
      $form_item.val(data_for_form[data_item]);
    }
  }

  var load_my_feedback_data = function(section_node, data){
    // Clean existing values
    $('.answer-value', section_node).empty();

    for(data_item in data){
      // either a place witin to list it or the outer location
      var fill_field = $('#list_' + data_item, section_node);
      if(fill_field.length < 1){
        fill_field = $('#assess_' + data_item, section_node);
      }
      var data_class = fill_field.data('class');
      for(var i=0; i<data[data_item].length; ++i){
        var node = $("<div/>");
        if(data_class && data_class.length > 0){
          node.addClass(data_class);
        }
        node.text(data[data_item][i]);
        fill_field.append(node);
      }

      var mean_field = $('#mean_' + data_item, section_node);
      mean_field.text(mean(data[data_item]));
    }
  }

  var _load_data = function (handler_name, args, post_data_fn){
    $.ajax({
      url: runtime.handlerUrl(element, handler_name),
      data: args,
      dataType: 'json',
      success: function(data){
        if(data.result && data.result == "error"){
          if(data.msg){
            alert(data.msg);
          }
          else{
            alert('Error loading feedback');
          }
        }
        else{
          post_data_fn(data);
        }
      },
      error: function(data){
        alert('Error loading feedback');
      }
    })
  }

  var load_data_for_peer = function (peer_id){
    _load_data('load_peer_feedback', 'peer_id=' + peer_id, function(data){load_data_into_form('peer_review', data);});
  }

  var load_data_for_other_group = function (group_id){
    _load_data('load_other_group_feedback', 'group_id=' + group_id, function(data){load_data_into_form('other_group_review', data);});
  }

  $('form.peer_review, form.other_group_review', element).on('submit', function(ev){
    ev.preventDefault();
    var $form = $(this);

    $form.find(':submit').prop('disabled', true);
    items = $form.serializeArray();
    data = {}
    $.each(items, function(i,v){
      data[v.name] = v.value;
    });

    $.ajax({
      type: $form.attr('method'),
      url: runtime.handlerUrl(element, $form.attr('action')),
      data: JSON.stringify(data),
      success: function(data){
        var msg = 'Thanks for your feedback!';
        if(data.msg){
          msg = data.msg;
        }
        alert(msg);
      },
      error: function(data){
        alert('Sorry, there was an error saving your feedback');
      },
      complete: function(data){
        $form.find(':submit').prop('disabled', false);
      }
    });

    return false;
  });

  var peers = JSON.parse($('.peer_group', element).html());
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
    $('.peers', element).append(peer_node(peers[i]));
  }

  var groups = JSON.parse($('.assess_groups', element).html());
  var group_node = function(group){
    var gn = $('<a class="select_group" />');
    var gi = $('<img class="avatar" />');
    gi.attr('src', group.img);
    gn.data('id', group.id);
    gn.append(gi);

    return gn;
  }

  for(var i=0; i < groups.length; ++i){
    $('.other_groups', element).append(group_node(groups[i]));
  }


  var step_map = JSON.parse($('.step_map', element).html());

  $(document).on('select_stage', function(target, selected_step_id){
    // Hide show correct content
    $('.revealer').removeClass('selected');
    $(this).addClass('selected');

    $('.activity_section').hide();

    // NOTE: use of ids specified by designer here
    $('#activity_' + selected_step_id).show();

    // Update step makers
    var step_pn = step_map[selected_step_id];
    $('.page-to.previous, .page-to.next', element).attr('title', '').off('click').removeAttr('href');
    if(step_pn.prev){
      var prev = step_map[step_pn.prev];
      $('.page-to.previous', element)
        .attr('title', prev.name)
        .on('click', function(){$("#" + step_pn.prev).click();}).attr('href', '#');
    }
    if(step_pn.next){
      var next_step = step_map[step_pn.next];
      if(next_step['restrict_message']){
        $('.page-to.next', element).attr('title', next_step['restrict_message']);
      }
      else{
        $('.page-to.next', element)
          .attr('title', next_step.name)
          .on('click', function(){$("#" + step_pn["next"]).click();}).attr('href', '#');
      }
    }
  });

  $('.revealer').on('click', function(ev){
    $(document).trigger('select_stage', $(this).attr('id'));

    ev.preventDefault();
    return false;
  });

  $('.view_feedback').on('click', function(ev){
    $('.feedback_sections').hide();
    $('.view_feedback').removeClass('selected');
    var showid = $(this).data('showid');
    $('.' + showid, element).show();
    $(this).addClass('selected');

    if(showid == "cohort_feedback"){
      _load_data('load_my_group_feedback', null, function(data){load_my_feedback_data($('.cohort_feedback', element), data);});
    }
    else{
      _load_data('load_my_peer_feedback', null, function(data){load_my_feedback_data($('.team_feedback', element), data);});
    }

    ev.preventDefault();
    return false;
  });

  $('.select_peer').on('click', function(ev){
    $('.select_peer,.select_group').removeClass('selected');
    $(this).addClass('selected');
    $('.other_group_review', element).hide();
    $('.peer_review', element).show();
    $('.peer_id', element).attr('value', $(this).data('id'));
    load_data_for_peer($(this).data('id'));

    ev.preventDefault();
    return false;
  });

  $('.select_group').on('click', function(ev){
    $('.select_peer,.select_group').removeClass('selected');
    $(this).addClass('selected');
    $('.other_group_review', element).show();
    $('.peer_review', element).hide();
    $('.group_id', element).attr('value', $(this).data('id'));
    $('.other_submission_links', element).empty().hide();
    load_data_for_other_group($(this).data('id'));

    ev.preventDefault();
    return false;
  });

  // activate the first step
  $(document).trigger("steps_available", step_map);
  $(document).trigger("select_stage", step_map["default"]);


  // Test Uploader code
  var upload_data = {
    dataType: 'json',
    url: runtime.handlerUrl(element, "upload_submission"),
    add: function(e, data){
      var target_form = $(e.target);
      $('.' + data.paramName + '_name', target_form).val(data.files[0].name);
      $('.' + data.paramName + '_label', target_form).text("Update");

      $(document).on('perform_uploads', function(ev){
        data.submit();
      });
    },
    done: function(e, data){
      //x = q;
      alert(data.result.message);
    }
  };

  $('.uploader', element).fileupload(upload_data);

  var upload_form = $('.upload_form', element).appendTo($(document.body));
  $('.cancel_upload', upload_form).on('click', function(){
    upload_form.hide();
  })
  $('.do_upload', upload_form).on('click', function(){
    $(document).trigger('perform_uploads');
    upload_form.hide();
  })

  $('.show_upload_form', element).on('click', function(){
    upload_form.show();
  });

  $('.view_other_submissions', element).on('click', function(){
    var $flyup = $('.other_submission_links', element);
    var is_visible = $flyup.is(":visible");
    $flyup.empty().hide();
    if(!is_visible){
      var selected_group_id = $('.select_group.selected').data("id");
      $.ajax({
        url: runtime.handlerUrl(element, "other_submission_links"),
        data: {group_id: selected_group_id},
        dataType: 'json',
        success: function(data){
          $flyup.html(data.html).show();
        },
        error: function(data){
          alert('Error loading links for group!!!');
        }
      });
    }
  });
}

// TODO: this function does way too much: might make sense to extract reviews, assessments, etc.
// into separate functions and make this function call them
function GroupProjectBlock(runtime, element) {

    function get_from_node(selector, default_value) {
        var the_node = $(selector, element);
        return (the_node.length > 0) ? the_node.html() : default_value;
    }
    var DATA_PRESENT_SUBMIT = get_from_node('.data-present-button-text', 'Resubmit');
    var NO_DATA_PRESENT_SUBMIT = get_from_node('.no-data-button-text', 'Submit');

    var message_box = $('.message', element).appendTo($(document.body));
    message_box.on('click', '.button, .close-box', function () {
        message_box.hide();
    });

    function show_message(msg) {
        message_box.find('.message_text').html(msg);
        message_box.show();
    }

    function mean(value_array) {
        var sum = 0;
        var count = value_array.length;
        if (count < 1) {
            return null;
        }

        for (var i = 0; i < count; ++i) {
            sum += parseFloat(value_array[i]);
        }

        return sum / count;
    }

    function load_my_feedback_data(section_node, data) {
        // Clean existing values
        $('.feedback-data', section_node).remove();

        for (var data_item in data) {
            if (!data.hasOwnProperty(data_item)) continue;
            // either a place witin to list it or the outer location
            var fill_field = $('#list_' + data_item, section_node);
            if (fill_field.length < 1) {
                fill_field = $('#assess_' + data_item, section_node);
            }
            var data_class = fill_field.data('class');

            for (var i = 0; i < data[data_item].length; ++i) {
                var node = $("<div class='feedback-data' />");
                if (data_class && data_class.length > 0) {
                    node.addClass(data_class);
                }
                node.html(data[data_item][i]);
                fill_field.append(node);
            }

            var mean_field = $('#mean_' + data_item, section_node);
            mean_field.text(Math.round(mean(data[data_item])));
        }
    }

    function _load_data(handler_name, args, form_node, post_data_fn) {
        $('.group-project-xblock-wrapper', element).addClass('waiting');
        form_node.find('.editable').attr('disabled', 'disabled');
        form_node.find('.answer').val(null);
        form_node.find('button.submit').html(NO_DATA_PRESENT_SUBMIT).attr('disabled', 'disabled');
        $.ajax({
            url: runtime.handlerUrl(element, handler_name),
            data: args,
            dataType: 'json',
            success: function (data) {
                if (data.result && data.result == "error") {
                    if (data.msg) {
                        show_message(data.msg);
                    }
                    else {
                        show_message('We encountered an error loading feedback.');
                    }
                }
                else {
                    post_data_fn(form_node, data);
                }
            },
            error: function (data) {
                show_message('We encountered an error loading feedback.');
            }
        }).done(function () {
            $('.group-project-xblock-wrapper', element).removeClass('waiting');
            form_node.find('.editable').removeAttr('disabled');
        });
    }

    var groups = JSON.parse($('.assess_groups', element).html());
    var group_node = function (group) {
        var gn = $('<a class="select_group" />');
        var gi = $('<span class="avatar"><i class="fa fa-users mk-icon-groupworknav" /></span>');
        gn.data('id', group.id);
        gn.append(gi);

        return gn;
    };

    // .other_groups is placeholder elem to inject list of groups to - it must be present in project XML if group review is enabled
    for (var i = 0; i < groups.length; ++i) {
        $('.other_groups', element).append(group_node(groups[i]));
    }


    // TODO: does not include activity_id - might need fixing when all activities are displayed simultaneously
    $(document).on('select_stage', function (target, selected_stage_id) {
        // can't use $('#'+selected_stage_id) as selected_stage_id contains slashes
        var stage = $("[id='"+selected_stage_id+"']", element);
        if (stage.length > 0) {
            $('.activity_section', element).hide();
            stage.show();
        }
    });

    $('.view_feedback').on('click', function (ev) {
        var showid = $(this).data('showid');

        var operation = (showid == "cohort_feedback") ? 'load_my_group_feedback' : 'load_my_peer_feedback';
        var selector = (showid == "cohort_feedback") ? '.group_assessment' : '.peer_assessment';

        _load_data(operation, null, $(selector, element), load_my_feedback_data);
        $(selector, element).show();

        $(document).trigger('data_loaded', {operation: operation});
        ev.preventDefault();
        return false;
    });



    var initialization_data = JSON.parse($('.initialization_data', element).html());
    if (initialization_data && initialization_data.default_stage_id) {
        $(document).trigger('select_stage', initialization_data.default_stage_id);
    }


    // TODO: a bit hacky solution to allow directly to stages
    // Remove when stages become actual XBlocks and jump_to_id supports jumping to children
    $(document).trigger('activity_initialized', element);
}

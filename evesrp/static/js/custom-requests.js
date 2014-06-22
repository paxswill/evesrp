/*
 * Make the link in button dropdowns submit the form
 */

function flash(message, category){
  var flashed = $("<div></div>");
  flashed.addClass("alert alert-dismissable fade in");
  flashed.addClass("alert-" + category);
  var close_button = $("<button>&times;</button>");
  close_button.attr('type', 'button');
  close_button.attr('data-dismiss', 'alert');
  close_button.addClass('close');
  flashed.append(close_button);
  flashed.append(message);
  $("#content").prepend(flashed);
}

function submitAction(e) {
  var $link = $(e.target);
  var form = $link.closest("form");
  form.find("input[name='type_']").attr("value", $link.attr("id"));
  $.post(
    window.location.pathname,
    form.serialize(),
    function() {
      var requestID = $('meta[name="srp_request_id"]').attr('content');
      $.getJSON(
        '/api/request/' + requestID + '/actions/',
        function(data) {
          var actionList = $('#actionList');
          // Re-render the actions list
          actionList.empty()
          actionList.append(Handlebars.templates.actions(data));
        }
      );
      $.getJSON(
        '/api/request/' + requestID + '/',
        function(data) {
          // Reset the action form
          form.find('textarea').val('');
          form.find('button.dropdown-toggle').dropdown('toggle');
          // Update the possible actions
          var actionMenu = form.find('ul.dropdown-menu');
          actionMenu.empty();
          actionMenu.append(Handlebars.templates.action_menu(data));
          // Update status
          var statusBadge = $('.request-status');
          statusBadge.removeClass('label-warning label-info label-success ' +
            'label-danger');
          statusBadge.addClass('label-' + statusColor(data.status));
          statusBadge.text(capitalize(data.status));
        }
      );
    }
  );
  return false;
};

$('form#actionForm ul').click(submitAction);
$('form#actionForm button[type="submit"]').click(submitAction);

$("ul#request-modifier-type li a").click( function(e) {
  var form = $(this).closest("form");
  form.find("input[name='type_']").attr("value", $(this).attr("id"));
  form.submit();
  return false;
});

$('#detailsModal form').submit(function() {
  var $form = $(this);
  $.post(
    window.location.pathname,
    $form.serialize(),
    function(data) {
      $('#request-details').text($form.find('textarea#details').val());
    }
  );
  $('#detailsModal').modal('hide')
  return false;
});

$('dd#payout span').tooltip()

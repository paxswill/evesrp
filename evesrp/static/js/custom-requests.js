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

function renderRequest(request) {
  var actionMenu = $('#actionMenu'),
      actionList = $('#actionList'),
      statusBadge = $('#request-status'),
      modifierList = $('#modifierList'),
      requestDetails = $('#request-details'),
      payout = $('#request-payout'),
      division = $('#request-division'),
      evaluatingOnly = $('.evaluating-only'),
      modifiers;
  // Update action menu
  actionMenu.empty();
  actionMenu.append(Handlebars.templates.action_menu(request));
  // Update list of actions
  actionList.empty()
  actionList.append(Handlebars.templates.actions(request));
  // Update status badge
  statusBadge.removeClass('label-warning label-info label-success ' +
    'label-danger');
  statusBadge.addClass('label-' + statusColor(request.status));
  statusBadge.text(capitalize(request.status));
  // Update the list of modifiers
  modifiers = $.map(request.modifiers, function(modifier) {
    if (modifier.void) {
      return Handlebars.templates.voided_modifier(modifier);
    } else if (request.status === 'evaluating' &&
        request.valid_actions.indexOf('approved') !== -1) {
      return Handlebars.templates.voidable_modifier(modifier);
    } else {
      return Handlebars.templates.modifier(modifier);
    }
  });
  modifierList.empty();
  modifierList.append(modifiers);
  // Update details
  requestDetails.text(request.details);
  // Update Payout
  payout.text(request.payout);
  // Disable modifier and payout forms if not evaluating
  if (request.status === 'evaluating') {
    evaluatingOnly.prop('disabled', false);
  } else {
    evaluatingOnly.prop('disabled', true);
  }
  // Update division
  division.text(request.division.name);
}

function submitAction(e) {
  var $link = $(e.target);
  var form = $link.closest("form");
  form.find("input[name='type_']").attr("value", $link.attr("id"));
  $.post(
    window.location.pathname,
    form.serialize(),
    function(data) {
      // Reset the action form
      form.find('textarea').val('');
      if (!$(e.target).hasClass('btn')) {
        form.find('button.dropdown-toggle').dropdown('toggle');
      }
      // Update everything
      renderRequest(data);
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

$('#request-payout').tooltip()

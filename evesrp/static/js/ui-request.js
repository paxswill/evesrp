var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.request = {

  render: function renderRequest(request) {
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
    statusBadge.addClass('label-' + EveSRP.util.statusColor(request.status));
    statusBadge.text(EveSRP.util.capitalize(request.status));
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
    payout.tooltip('destroy');
    payout.tooltip({
      title: 'Base Payout: ' + request.base_payout_str,
      placement: 'right'
    });
    payout.text(request.payout_str);
    // Disable modifier and payout forms if not evaluating
    if (request.status === 'evaluating') {
      evaluatingOnly.prop('disabled', false);
    } else {
      evaluatingOnly.prop('disabled', true);
    }
    // Update division
    division.text(request.division.name);
  },

  submitAction: function submitAction(ev) {
    var $link = $(ev.target);
    var form = $link.closest("form");
    form.find("input[name='type_']").attr("value", $link.attr("id"));
    $.post(
      window.location.pathname,
      form.serialize(),
      function(data) {
        // Reset the action form
        form.find('textarea').val('');
        if (!$link.hasClass('btn')) {
          form.find('button.dropdown-toggle').dropdown('toggle');
        }
        // Update everything
        EveSRP.ui.request.render(data);
      }
    );
    return false;
  },

  submitModifier: function submitModifier() {
    var $this_ = $(this),
        $form = $this_.closest('form');
    // Set the hidden 'type_' field to the kind of modifier this is
    $form.find("input[name='type_']").attr("value", $this_.attr("id"));
    // toggle the dropdown back up
    $form.find('button.dropdown-toggle').dropdown('toggle');
    $.ajax( {
      type: 'POST',
      url: window.location.pathname,
      data: $form.serialize(),
      success: function addModifierSuccess(data) {
        // reset the inputs when it's successful
        $form.find('textarea').val('');
        $form.find('input#value').val('');
      },
      complete: function addModifierComplete(jqxhr) {
        EveSRP.ui.request.render(jqxhr.responseJSON);
      }
    });
    return false;
  },

  voidModifier: function voidModifier(ev) {
    var $form = $(ev.target);
    $.post(
      window.location.pathname,
      $form.serialize(),
      function(data) {
        // Update
        EveSRP.ui.request.render(data);
      }
    );
    return false;
  },

  setPayout: function setPayout() {
    var $form = $(this);
    $.post(
      window.location.pathname,
      $form.serialize(),
      function(data) {
        // Reset
        $form.find('input#value').val('');
        // Update
        EveSRP.ui.request.render(data);
      }
    );
    return false;
  },

  updateDetails: function updateDetails() {
    var $form = $(this);
    $.post(
      window.location.pathname,
      $form.serialize(),
      function(data) {
        EveSRP.ui.request.render(data);
      }
    );
    $('#detailsModal').modal('hide')
    return false;
  },

  setupEvents: function setupRequestEvents() {
    // Attach listeners for the action button/dropdown
    $('form#actionForm ul').click(EveSRP.ui.request.submitAction);
    $('form#actionForm button[type="submit"]').click(
      EveSRP.ui.request.submitAction);
    // event handler for adding modifiers
    $('ul#request-modifier-type li a').click(EveSRP.ui.request.submitModifier);
    // event handler for voiding modifiers
    $('#modifierList').submit(EveSRP.ui.request.voidModifier);
    // event handler for setting the base payout
    $('form#payoutForm').submit(EveSRP.ui.request.setPayout);
    // event handler for updating the request details
    $('#detailsModal form').submit(EveSRP.ui.request.updateDetails);
    // Add the tooltip showing the base payout
    $('#request-payout').tooltip({
      title: $('#request-payout').data('initial-title'),
      placement: 'right'
    });
  },
};
EveSRP.ui.request.setupEvents();

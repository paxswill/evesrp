unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/tooltip'
require 'bootstrap/js/dropdown'
require 'bootstrap/js/modal'
util = require './util'
ui = require './common-ui'
Jed = require 'jed'
capitalize = require 'underscore.string/capitalize'
actionMenuTemplate = require './templates/action_menu'
actionsTemplate = require './templates/actions'
voidedModifierTemplate = require './templates/voided_modifier'
voidableModifierTemplate = require './templates/voidable_modifier'
modifierTemplate = require './templates/modifier'


render = (request) ->
    # Update the action menu
    $actionMenu = jQuery '#actionMenu'
    $actionMenu.empty()
    $actionMenu.append (actionMenuTemplate request)
    # Update action log
    $actions = jQuery '#actionList'
    $actions.empty()
    $actions.append (actionsTemplate request)
    # Update status badge
    $statusBadge = jQuery '#request-status'
    $statusBadge.removeClass \
        'label-warning label-info label-success label-danger'
    $statusBadge.addClass "label-#{ util.statusColor request.status }"
    $statusBadge.text (ui.i18n.gettext (capitalize request.status))
    # Update modifiers log
    if modifiers?
        modifiers = for modifier in request.modifiers
            if modifier.void
                voidedModifierTemplate modifier
            else if request.status == 'evaluating' and \
                    'approved' in request.valid_actions
                voidableModifierTemplate modifier
            else
                modifierTemplate modifier
        $modifierList = jQuery '#modifierList'
        $modifierList.empty()
        $modifierList.append modifiers
    # Update details and division
    (jQuery '#request-details').text request.details
    (jQuery '#request-division').text request.division.name
    # Update Payout
    $payout = jQuery '#request-payout'
    $payout.tooltip 'destroy'
    translated = ui.i18n.gettext "Base Payout: %(base_payout)s"
    $payout.tooltip {
        title: Jed.sprintf translated, {base_payout: request.base_payout_str}
        placement: 'right'
    }
    $payout.text request.payout_str
    # Disable modifier and payout forms if not evaluating
    $evaluatingOnly = jQuery '.evaluating-only'
    $evaluatingOnly.prop 'disabled', (request.status != 'evaluating')
    # Set links for attributes (previously called "transformed attributes")
    if request.transformed?
        for attr, link of request.transformed
            $element = jQuery "##{ attr }"
            text = request[attr]
            if attr == 'status'
                $element = $statusBadge
            else if attr == 'pilot'
                text = request.pilot.name
            # TODO: HTML Escape `text`
            $element.html "a href=\"#{ link }\" target=\"_blank\">#{ text }<i class\"fa fa-external-link\"></i></a>"


submitAction = (ev) ->
    $target = jQuery ev.target
    $form = $target.closest 'form'
    # Don't try submitting opening a dropdown toggle
    if ($target.prop 'nodeName') != 'A' and $target.hasClass 'dropdown-toggle'
        return true
    ($form.find "input[name='type_']").val ($target.attr 'id')
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        success: (data) ->
            # Reset the action form
            ($form.find 'textarea').val ''
            unless $target.hasClass 'btn'
                ($form.find 'button.dropdown-toggle').dropdown 'toggle'
        complete: (jqxhr) ->
            # Update everything
            render jqxhr.responseJSON
    }
    false


submitModifier = () ->
    $this = jQuery this
    $form = $this.closest 'form'
    # Set the hidden 'type_' field to the type of modifier this is
    ($form.find "input[name='type_']").val ($this.attr 'id')
    # close the dropdown
    ($form.find 'button.dropdown-toggle').dropdown 'toggle'
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        success: (data) ->
            ($form.find 'textarea').val ''
            ($form.find 'input#value').val ''
        complete: (jqxhr) ->
            render jqxhr.responseJSON
    }
    false


voidModifier = (ev) ->
    $form = jQuery ev.target
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        complete: (jqxhr) ->
            # Update everything
            render jqxhr.responseJSON
    }
    false


setPayout = (ev) ->
    $form = jQuery this
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        success: (data) ->
            ($form.find 'input#value').val ''
        complete: (jqxhr) ->
            # Update everything
            render jqxhr.responseJSON
    }
    false


updateDetails = (ev) ->
    $form = jQuery ev.target
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        complete: (jqxhr) ->
            # Update everything
            render jqxhr.responseJSON
    }
    (jQuery '#detailsModal').modal 'hide'
    false


setupEvents = () ->
    # Add event listeners for ajax-y goodness
    (jQuery '#actionMenu').on 'click', submitAction
    (jQuery 'ul#request-modifier-type li a').on 'click', submitModifier
    (jQuery '#modifierList').on 'submit', voidModifier
    (jQuery 'form#payoutForm').on 'submit', setPayout
    (jQuery '#detailsModal form').on 'submit', updateDetails
    # Add tooltip showing base payout
    $payoutElement = jQuery '#requests-payout'
    $payoutElement.tooltip {
        title: $payoutElement.data 'initial-title'
        placement: 'right'
    }


exports.setupEvents = setupEvents

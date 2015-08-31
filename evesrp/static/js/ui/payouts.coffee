unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/tooltip'
require 'bootstrap/js/popover'
util = require '../util'
ui = require './common'
filter = require './filter'
payoutTemplate = require '../templates/payout_panel'


# Initialize to parse time, trying to prevent refreshes immediately upon
# scrolling.
lastRefresh = (new Date).getTime()
# Limit refreshes to every 7 seconds
refreshDelay = 7000


renderRequest = (request) ->
    $panelList = jQuery '#requests'
    $panel = $panelList.find "#request-#{ request.id }"
    $newPanel = jQuery payoutTemplate request
    if $panel.length != 0
        # Remove old listeners and popovers/tooltips
        $copyButtons = $panel.find '.copy-btn'
        $copyButtons.tooltip 'destroy'
        ui.client.unclip $copyButtons
        ($panel.find '.small-popover').popover 'destroy'
        # if this panel is expanded, keep it expanded
        unless ($panel.find 'table.in').length == 0
            ($newPanel.find 'table.collapse').addClass 'in'
        $panel.replaceWith $newPanel
    else
        $panelList.append $newPanel
    # Attach events and activate tooltips and popovers on the new panel
    $panel = $panelList.find "#request-#{ request.id }"
    $copyButtons = $panel.find '.copy-btn'
    ui.client.clip $copyButtons
    $copyButtons.tooltip {trigger: 'manual'}
    # Find the popover elements, prevent their default actions, and activate
    # the popovers on them.
    (($panel.find '.small-popover').on 'click', false).popover()
    (jQuery '.null-link').on 'click', (ev) ->
        ev.preventDefault()


markPaid = (ev) ->
    $form = (jQuery ev.target).closest 'form'
    jQuery.ajax {
        type: 'POST'
        url: $form.attr 'action'
        data: $form.serialize()
        success: renderRequest
    }
    # Attempt to refresh requests
    getRequests()
    false


copyUpdate = (client, args) ->
    # event handler for the ZeroClipboard copy event
    timeStamp = (new Date).getTime()
    $panel = (jQuery this).clsoest '.panel'
    if (timestamp - lastRefresh) > refreshDelay
        updateRequest $panel.data 'request-id'


getRequests = () ->
    timestamp = (new Date).getTime()
    # Respect cooldown between mass updates
    if (timestamp - lastRefresh) <= refreshDelay then return
    # Reset cooldown timer, do a mass update
    lastRefresh = timestamp
    jQuery.ajax {
        type: 'GET'
        url: window.location.pathname
        success: (data) ->
            for request in data.requests
                renderRequest request
    }


updateRequest = (requestID) ->
    # Updating an individual request is not bound to the cooldown timer, as
    # these updates are done to try to prevent two people from modifiying the
    # same request at once.
    # TODO: Add actual locking to the app for requests
    jQuery.ajax {
        type: 'GET'
        url: "$SCRIPT_ROOT/request/#{ requestID }"
        success: renderRequest
    }


infiniteScroll = (ev) ->
    $window = jQuery window
    $document = jQuery document
    if $window.scrollTop() > ($document.height() - $window.height() - 300)
        getRequests()


setupEvents = () ->
    # Clipboard setup
    ui.setupClipboard()
    ui.client.on 'complete', copyUpdate
    # Tooltips
    $copyBtns = (jQuery '.copy-btn')
    $copyBtns.tooltip {trigger: 'manual'}
    $copyBtns.on 'mouseover', (ev) ->
        (jQuery this).tooltip 'show'
    $copyBtns.on 'mouseout', (ev) ->
        (jQuery this).tooltip 'hide'
    # Popovers
    ((jQuery '.small-popover').on 'click', false).popover()
    # Mark requests as paid
    (jQuery '#requests').on 'submit', markPaid
    # History and filters setup
    $window = jQuery window
    $window.on 'popstate', getRequests
    $window.on 'evesrp:filterchange', getRequests
    # Add infinite scrolling
    $window.on 'scroll', infiniteScroll
    # Prevent default action, but not bubbling for the links to expand the
    # list of actions for a request
    (jQuery '.null-link').on 'click', (ev) ->
        ev.preventDefault()


exports.setupEvents = setupEvents

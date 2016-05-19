unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/tooltip'
require 'bootstrap/js/popover'
ui = require 'evesrp/common-ui'
clipboard = require 'evesrp/clipboard'
filter = require 'evesrp/filter'
payoutTemplate = require 'evesrp/templates/payout_panel'


# Initialize to parse time, trying to prevent refreshes immediately upon
# scrolling.
lastRefresh = (new Date).getTime()
# Limit refreshes to every 7 seconds
refreshDelay = 7000


renderRequest = (request) ->
    $panelList = jQuery '#requests'
    $panel = $panelList.find "#request-#{ request.id }"
    bothPromise = jQuery.when ui.setupTranslations(), ui.setupFormats()
    bothPromise.done () ->
        $newPanel = jQuery (payoutTemplate request)
        if $panel.length != 0
            # Remove clipboard handlers for the old copy buttons
            $copyButtons = $panel.find '.copy-btn'
            clipboard.unclip $copyButtons
            # Hide tooltips and popovers
            $copyButtons.tooltip 'hide'
            ($panel.find '.small-popover').popover 'hide'
            # if this panel is expanded, keep it expanded
            unless ($panel.find 'table.in').length == 0
                ($newPanel.find 'table.collapse').addClass 'in'
            $panel.replaceWith $newPanel
        else
            $panelList.append $newPanel
        # Attach events and activate popovers on the new panel
        $panel = $panelList.find "#request-#{ request.id }"
        $copyButtons = $panel.find '.copy-btn'
        clipboard.clip $copyButtons


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
    $panel = (jQuery this).closest '.panel'
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
        url: "#{ scriptRoot }/request/#{ requestID }"
        success: renderRequest
    }


infiniteScroll = (ev) ->
    $window = jQuery window
    $document = jQuery document
    if $window.scrollTop() > ($document.height() - $window.height() - 300)
        getRequests()


setupEvents = () ->
    # Clipboard setup
    clipboard.setup().done () ->
        clipboard.attachCopy copyUpdate
    # Tooltips
    $requests = jQuery '#requests'
    $requests.tooltip {
        trigger: 'hover focus'
        html: false
        selector: '.copy-btn'
    }
    # Popovers
    $requests.popover {
        trigger: 'focus'
        html: true
        selector: '.small-popover'
    }
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
    $requests.on 'click', '.null-link', (ev) ->
        ev.preventDefault()


exports.setupEvents = setupEvents

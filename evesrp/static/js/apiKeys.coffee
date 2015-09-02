unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/tooltip'
ui = require './common-ui'
apiKeyTemplate = require './templates/api_keys'


render = (data) ->
    $table = jQuery '#apikeys'
    $heading = table.find 'tr:first'
    $oldRows = (($table.find 'tr').not ':first').not ':last'
    $copyButtons = $oldRows.find '.copy-btn'

    # Remove tooltips and detach clipboard events
    ui.client.unclip $copyButtons
    # TODO: WTH am I redoing a search I just did (for .copy-btn)?
    for btn in $copyButtons.find '.copy-btn'
        (jQuery btn).tooltip 'destroy'
    $oldRows.remove ()
    
    if data.api_keys.length != 0
        $newRows = jQuery (apiKeyTemplate data)
        $copyButtons = $newRows.find '.copy-btn'
        ui.clipboardClient.clip $copyButtons
        $copyButtons.tooltip {
            placement: 'bottom'
            title: 'Copy to clipboard'
            trigger: 'manual focus'
        }
    else
        $newRows = jQuery '<tr><td class="text-center" colspan="3">No API
                           keys created.</td></tr>'
    $heading.after $newRows


modifyKey = (ev) ->
    $form = (jQuery ev.target).closest 'form'
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
        complete: (jqxhr) ->
            render(jqxhr.responseJSON)
    }
    false


setupEvents = () ->
    ui.setupClipboard()
    (jQuery '#apiKeys').on 'submit', modifyKey
    (jQuery '#createKey').on 'submit', modifyKey


exports.setupEvents = setupEvents

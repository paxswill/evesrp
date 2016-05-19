unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/tooltip'
ui = require 'evesrp/common-ui'
clipboard = require 'evesrp/clipboard'
apiKeyTemplate = require 'evesrp/templates/api_keys'


render = (data) ->
    $table = jQuery '#apikeys'
    $heading = table.find 'tr:first'
    $oldRows = (($table.find 'tr').not ':first').not ':last'
    $copyButtons = $oldRows.find '.copy-btn'
    i18nPromise = ui.setupTranslations()
    globalizePromise = ui.setupFormats()
    (jQuery.when i18nPromise, globalizePromise).done () ->
        # Remove tooltips and detach clipboard events
        clipboard.unclip $copyButtons
        # TODO: WTH am I redoing a search I just did (for .copy-btn)?
        for btn in $copyButtons.find '.copy-btn'
            (jQuery btn).tooltip 'destroy'
        $oldRows.remove()
        
        if data.api_keys.length != 0
            $newRows = jQuery (apiKeyTemplate data)
            $copyButtons = $newRows.find '.copy-btn'
            clipboard.clip $copyButtons
            $copyButtons.tooltip {
                placement: 'bottom'
                title: ui.i18n.gettext 'Copy to clipboard'
                trigger: 'manual focus'
            }
        else
            apiKeyText = ui.i18n.gettext "No API keys have been created."
            $newRows = jQuery "<tr><td class=\"text-center\" colspan=\"3\">#{ apiKeyText }</td></tr>"
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
    clipboard.setup()
    (jQuery '#apiKeys').on 'submit', modifyKey
    (jQuery '#createKey').on 'submit', modifyKey


exports.setupEvents = setupEvents

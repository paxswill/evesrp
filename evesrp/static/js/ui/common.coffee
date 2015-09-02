unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/alert'
_ = require 'underscore'
ZeroClipboard = require 'zeroclipboard'
flashTemplate = require '../templates/flash'


setLanguage = (ev) ->
    $target = jQuery ev.target
    $form = $target.closest 'form'
    ($form.find '#lang').val ($target.data 'lang')
    $form.submit()
    false


renderFlashes = (data) ->
    $content = jQuery '#content'
    for flashInfo in data.flashed_messages
        do (flashInfo) ->
            flashID = _.uniqueId()
            flashInfo.id = flashID
            flash = flashTemplate flashInfo
            $content.prepend flash
            closeFunction = () ->
                (jQuery "#flash-#{ flashID }").alert 'close'
            window.setTimeout closeFunction, 5000


renderNavbar = (data) ->
    for badgeName, count of data.nav_counts
        $badge = jQuery "#badge-#{ badgeName }"
        $badge.text (if count != 0 then count else '')


setupEvents = () ->
    # Update the nav bar and render any messages with every AJAX response
    (jQuery document).ajaxComplete (ev, jqxhr) ->
        data = jqxhr.responseJSON
        if data && 'flashed_messages' of data
            renderFlashes(data)
        if data && 'nav_counts' of data
            renderNavbar(data)
    (jQuery '.langSelect').on 'click', setLanguage


setupClipboard = () ->
    ZeroClipboard.config {swfPath: "#{ $SCRIPT_ROOT }/static/ZeroClipboard.swf"}
    client = new ZeroClipboard (jQuery '.copy-btn')
    exports.client = client


exports.setupEvents = setupEvents
exports.setupClipboard = setupClipboard

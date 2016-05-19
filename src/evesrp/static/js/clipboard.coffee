unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/modal'
Clipboard = require 'clipboard'
ZeroClipboard = require 'zeroclipboard'
sprintf = (require 'sprintf-js').sprintf
ui = require 'evesrp/common-ui'


setupPromise = null


setupClipboard = () ->
    if setupPromise != null
        return setupPromise
    setupPromise = jQuery.Deferred()
    # Check for HTML5 clipboard support.
    unless document.queryCommandSupported 'copy'
        zClient = setupZeroClipboard()
        zClient.on 'error', (ev) ->
            setupClipboardJS()
        zClient.on 'ready', (ev) ->
            zClient.on 'copy', (copyEvent) ->
                for handler in copyHandlers
                    handler copyEvent
            setupPromise.resolve()
    else
        setupClipboardJS()
    return setupPromise


setupZeroClipboard = () ->
    # Attempt to setup ZeroClipboard if HTML5 not supported
    ZeroClipboard.config {swfPath: "#{ scriptRoot }/static/ZeroClipboard.swf"}
    zClient = new ZeroClipboard (jQuery '.copy-btn')
    zClient.on 'error', (ev) ->
        # Clean up the ZeroCLipboard object if there's an error
        zClient.destroy()
        module.zClient = null
    module.zClient = zClient
    return zClient


setupClipboardJS = () ->
    # Two possiblilities.
    # 1) HTML5 clipboard access is supported
    # 2) No HTML5 support, but Flash isn't working either (Hello Safari)
    jClient = new Clipboard '.copy-btn'
    # Now to handle scenario #2
    # Set up the modal and variables
    $copyModal = jQuery '#copyModal'
    $document = jQuery document
    hideHandler = (ev) ->
        $copyModal.modal 'hide'
        $document.off 'copy.evesrp', hideHandler
    # Update the text in the modal to match the current platform
    ui.setupTranslations().done () ->
        translatedText = ui.i18n.gettext 'Press %(key_combo)s to Copy.'
        if /Mac/i.test navigator.userAgent
            keyCombo = '⌘-C'
        else
            keyCombo = 'Ctrl-C'
        newText = sprintf translatedText, {key_combo: keyCombo}
        ($copyModal.find '#keyComboMessage').text newText
    # Show the modal when Clipboard.js encounters an error
    jClient.on 'error', (ev) ->
        $copyModal.modal()
        $document.on 'copy.evesrp', hideHandler
    # Fire handlers for copy events
    jClient.on 'error', (ev) ->
        for handler in copyHandlers
            handler ev
    jClient.on 'success', (ev) ->
        for handler in copyHandlers
            handler ev
    module.jClient = jClient
    setupPromise.resolve()


clip = (elements) ->
    # Only ZeroClipboard needs to clip/unclip individual items.
    if module.zClient?
        module.zClient.clip elements


unclip = (elements) ->
    # Only ZeroClipboard needs to clip/unclip individual items.
    if module.zClient?
        module.zClient.unclip elements


copyHandlers = []


attachCopy = (handler) ->
    copyHandlers.push handler


exports.setup = setupClipboard
exports.clip = clip
exports.unclip = unclip
exports.attachCopy = attachCopy

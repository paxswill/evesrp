unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/alert'
_ = require 'underscore'
ZeroClipboard = require 'zeroclipboard'
flashTemplate = require './templates/flash'
sprintf = require 'underscore.string/sprintf'
Jed = require 'jed'


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


setupTranslations = () ->
    currentLang = document.documentElement.lang
    setupFormats currentLang
    if currentLang == 'en'
        # message keys are in English anyways, so we can use a default Jed
        exports.i18n = new Jed {}
    else
        getTranslation = jQuery.ajax {
            type: 'GET'
            url: "#{ $SCRIPT_ROOT }/static/translations/#{ currentLang }.json"
            success: (data) ->
                exports.i18n = new Jed {
                    missing_key_callback: (key, domain) ->

                        errorMessage = sprintf "'%s' not found in domain '%s'", key, domain
                        console.log errorMessage
                    locale_data: data.locale_data
                    domain: data.domain
                }
        }


setupFormats = (language) ->
    # TODO: handle those platforms that don't have Intl (useing the polyfill)
    if language == 'en'
        locales = "en"
    else
        # Fallback to English formatting if the requested locale is not
        # supported.
        locales = [language, "en"]
    # The only currency we're formatting is Eve ISK, which is a fictional
    # currency.
    exports.currencyFormat = new Intl.NumberFormat locales, {
        style: 'decimal'
        useGrouping: true
        minimumFractionDigits: 2
        maximumFractionDigits: 2
    }
    exports.percentFormat = new Intl.NumberFormat locales, {
        style: 'percent'
    }
    exports.numberFormat = new Intl.NumberFormat locales, {}
    # Always use 24-hour time and UTC for Eve
    exports.dateFormat = new Intl.DateFormat locales, {
        timeZone: 'UTC'
        hour12: false
        year: 'numeric'
        month: 'narrow'
        day: '2-digit'
        hour: '2-digit'
        minute: 'numeric'
    }



exports.setupEvents = setupEvents
exports.setupClipboard = setupClipboard
exports.setupTranslations = setupTranslations

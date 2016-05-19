unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/alert'
_ = require 'underscore'
humanize = require 'underscore.string/humanize'
titleize = require 'underscore.string/titleize'
flashTemplate = require 'evesrp/templates/flash'
sprintf = (require 'sprintf-js').sprintf
Jed = require 'jed'
Globalize = require 'globalize/dist/globalize-runtime'
# Load the Globalize parts we need
require 'globalize/dist/globalize-runtime/number'
require 'globalize/dist/globalize-runtime/date'


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


module.i18nPromise = null


setupTranslations = () ->
    if module.i18nPromise?
        return module.i18nPromise
    currentLang = document.documentElement.lang
    module.i18nPromise = jQuery.Deferred()
    jQuery.ajax {
        type: 'GET'
        url: "#{ scriptRoot }/static/translations/#{ currentLang }.json"
        success: (data) ->
            exports.i18n = new Jed {
                missing_key_callback: (key, domain) ->
                    # Not translating this message as it's only shwon in
                    # the console log.
                    errorMessage = sprintf "'%s' not found in domain '%s'", key, domain
                    console.log errorMessage
                    if windowRaven?
                        window.Raven.captureMessage errorMessage, {
                            level: 'warning'
                            extra: {
                                key: key,
                                domain: domain,
                                language: currentLang
                            }
                        }
                locale_data: data.locale_data
                domain: data.domain
            }
            module.i18nPromise.resolve()
    }
    return module.i18nPromise


module.globalizePromise = null


setupFormats = (locale) ->
    # find the locale for the current apge if not given one
    unless locale?
        locale = document.documentElement.lang
    # Defer to the currently running Promise if it exists
    if module.globalizePromise?
        return module.globalizePromise
    # Load the precompiled Globalize formatters for this locale
    module.globalizePromise = jQuery.Deferred()
    # Instead of using likely subtags, we're doing it ourselves for the cluple
    # of locales we support the would need likely subtags
    if locale == 'en-US'
        locale = 'en'
    Globalize = require "evesrp/globalize-#{ locale }"
    Globalize.locale locale
    # The only currency we're formatting is Eve ISK, which is a fictional
    # currency (so it won't be in the CLDR data, and I don't want to write
    # my own data file).
    exports.currencyFormat = Globalize.numberFormatter {
        style: 'decimal'
        maximumFractionDigits: 2
        minimumFractionDigits: 2
        round: 'truncate'
        useGrouping: true
    }
    exports.percentFormat = Globalize.numberFormatter {
        style: 'percent'
    }
    exports.numberFormat = Globalize.numberFormatter {
        style: 'decimal'
    }
    exports.dateFormatShort = Globalize.dateFormatter {
        datetime: 'short'
    }
    exports.dateFormatMedium = Globalize.dateFormatter {
        datetime: 'medium'
    }
    module.globalizePromise.resolve()
    return module.globalizePromise


attributeGettext = (attribute) ->
    # Helper for a common-ish pattern of
    # decapitalize(gettext(capitalize(attr))). Also used in the filter.coffee
    # file.
    # TODO: As in capitalizeHelper, is i18n needed here?
    humanizedAttribute = humanize attribute
    translatedAttribute = exports.i18n.gettext (titleize attribute)
    translatedAttribute.toLowerCase()


exports.setupEvents = setupEvents
exports.setupTranslations = setupTranslations
exports.setupFormats = setupFormats
exports.attributeGettext = attributeGettext

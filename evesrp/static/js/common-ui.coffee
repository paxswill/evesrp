unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/alert'
_ = require 'underscore'
ZeroClipboard = require 'zeroclipboard'
humanize = require 'underscore.string/humanize'
titleize = require 'underscore.string/titleize'
flashTemplate = require 'evesrp/templates/flash'
sprintf = require 'underscore.string/sprintf'
Jed = require 'jed'
Globalize = require 'globalize'


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
    ZeroClipboard.config {swfPath: "#{ scriptRoot }/static/ZeroClipboard.swf"}
    client = new ZeroClipboard (jQuery '.copy-btn')
    exports.client = client


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
                locale_data: data.locale_data
                domain: data.domain
            }
            module.i18nPromise.resolve()
    }
    return module.i18nPromise


module.globalizePromise = null


setupFormats = (locale) ->
    unless locale?
        locale = document.documentElement.lang
    # This chunk of code is lightly modified from the globalize docs
    if module.globalizePromise?
        return module.globalizePromise
    # Load likelySubtags in to Globalize first, then create the instance to see
    # what normalized language tag Globalize/CLDR is expecting. From there we
    # use that language tag to download the correct language. See link for more
    # details: https://gist.github.com/rxaviers/bb143a6715d1392ecc96
    cldrRoot = "#{ scriptRoot }/static/cldr"
    subTagsGet = jQuery.getJSON "#{ cldrRoot }/supplemental/likelySubtags.json"
    module.globalizePromise = jQuery.Deferred()
    subTagsGet.done (data) ->
        Globalize.load data
        tempGlobalize = new Globalize locale
        # Note: the Gist above uses languageId, but it seems Globalize has
        # moved on and now uses minlanguageId (note the lower-case 'L').
        languageTag = tempGlobalize.cldr.attributes.minlanguageId
        cldrGet = jQuery.when(
            jQuery.getJSON("#{ cldrRoot }/main/#{ languageTag }/ca-gregorian.json"),
            jQuery.getJSON("#{ cldrRoot }/main/#{ languageTag }/timeZoneNames.json"),
            jQuery.getJSON("#{ cldrRoot }/main/#{ languageTag }/numbers.json"),
            jQuery.getJSON("#{ cldrRoot }/supplemental/numberingSystems.json"),
            jQuery.getJSON("#{ cldrRoot }/supplemental/timeData.json"),
            jQuery.getJSON("#{ cldrRoot }/supplemental/weekData.json")
        )
        cldrGet.done () ->
            argsArray = [].slice.apply arguments, [0]
            argsArray.map (data) -> Globalize.load data[0]
            localeGlobalize = new Globalize locale
            # The only currency we're formatting is Eve ISK, which is a fictional
            # currency (so it won't be in the CLDR data, and I don't want to write
            # my own data file).
            exports.currencyFormat = localeGlobalize.numberFormatter {
                style: 'decimal'
                maximumFractionDigits: 2
                minimumFractionDigits: 2
                round: 'truncate'
                useGrouping: true
            }
            exports.percentFormat = localeGlobalize.numberFormatter {
                style: 'percent'
            }
            exports.numberFormat = localeGlobalize.numberFormatter {
                style: 'decimal'
            }
            exports.dateFormatShort = localeGlobalize.dateFormatter {
                datetime: 'short'
            }
            exports.dateFormatMedium = localeGlobalize.dateFormatter {
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
exports.setupClipboard = setupClipboard
exports.setupTranslations = setupTranslations
exports.setupFormats = setupFormats
exports.attributeGettext = attributeGettext

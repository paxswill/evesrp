jQuery = require 'jquery'
Handlebars = require 'handlebars/runtime'
_ = require 'underscore'
capitalize = require 'underscore.string/capitalize'
sprintf = require 'underscore.string/sprintf'
util = require 'evesrp/util'
ui = require 'evesrp/common-ui'


csrf = () -> 
    token = jQuery "meta[name='csrf_token']"
    token.attr "content"


capitalizeHelper = (str) ->
    # TODO: I8N-ize, maybe?
    capitalize str


datefmt = (date, options) ->
    style = options.hash.style ? 'medium'
    date = util.localToUTC date
    if style == 'medium'
        ui.dateFormatMedium date
    else if style == 'short'
        ui.dateFormatShort date
    else
        console.log "Invalid datetime style: #{ style }"
        ui.dateFormatterMedium date


currencyFormat = (currency) ->
    if typeof currency == "string"
        currency = parseFloat currency
    ui.currencyFormat currency


numberFormat = (number) ->
    if typeof number == "string"
        number = parseFloat number
    ui.numberFormat number


percentFormat = (percent) ->
    if typeof number == "string"
        percent = parseFloat percent
    ui.percentFormat percent


statusColor = (status) ->
    util.statusColor status


compare = (left, right, options) ->
    handlebarsThis = this
    call = (bool) ->
        if bool
            return options.fn handlebarsThis
        else
            return options.inverse handlebarsThis

    op = options.hash.operator ? "==="
    switch op
        # coffeescript converts == to ===
        when "==", "===" then call (left == right)
        when "!=", "!==" then call (left != right)
        when "<" then call (left < right)
        when ">" then call (left > right)
        when "<=" then call (left <= right)
        when ">=" then call (left >= right)
        when "in" then call (left in right)
        when "of" then call (left of right)
        else call (left == right)


count = (collection) ->
    collection.length


gettext = (msgid, options) ->
    translated = ui.i18n.gettext msgid
    if _.isEmpty options.hash
        escaped = Handlebars.escapeExpression translated
        return new Handlebars.SafeString escaped
    else
        args = _.mapObject options.hash, Handlebars.escapeExpression
        return new Handlebars.SafeString (sprintf translated, args)


transformed = (request, attr) ->
    if attr of request.transformed
        safeText = Handlebars.escapeExpression request[attr]
        return new Handlebars.SafeString \
        "<a href=\"#{ request.transformed[attr] }\"
            target=\"_blank\">#{ safeText }
         <i class=\"fa fa-external-link\"></i></a>"
    request[attr]


modifierHeader = (modifier) ->
    if modifier.type == "absolute"
        amount = (parseFloat modifier.value) / 1000000
        amount = ui.numberFormat amount
        if modifier.value >= 0
            localized = ui.i18n.gettext "%(amount)sM ISK bonus"
        else
            localized = ui.i18n.gettext "%(amount)sM ISK penalty"
    else if modifier.type == "relative"
        amount = ui.percentFormat (parseFloat modifier.value)
        if modifier.value >= 0
            localized = ui.i18n.gettext "%(amount)s bonus"
        else
            localized = ui.i18n.gettext "%(amount)s penalty"
    escaped = Handlebars.escapeExpression (sprintf localized, {amount: amount})
    return new Handlebars.SafeString escaped

urlize = (str, options) ->
    limit =  options.hash?.limit
    escaped = Handlebars.escapeExpression str
    return new Handlebars.SafeString (util.urlize escaped, limit)


registerHelpers = (handlebars) ->
    handlebars.registerHelper({
        attr_gettext: ui.attributeGettext
        csrf: csrf
        capitalize: capitalizeHelper
        currencyfmt: currencyFormat
        numberfmt: numberFormat
        percentfmt: percentFormat
        datefmt: datefmt
        status_color: statusColor
        compare: compare
        count: count
        transformed: transformed
        gettext: gettext
        modifier_header: modifierHeader
        urlize: urlize
    })
    return handlebars


exports.registerHelpers = registerHelpers

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
        return new Handlebars.SafeString translated
    else
        args = _.mapObject options.hash, Handlebars.Utils.escapeExpression
        return new Handlebars.SafeString (sprintf translated, args)


transformed = (request, attr) ->
    if attr of request.transformed
        return new Handlebars.SafeString \
        "<a href=\"#{ request.transformed[attr] }\"
            target=\"_blank\">#{ request[attr] }
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
    return new Handlebars.SafeString (sprintf localized, {amount: amount})


sortEntities = (list) ->
    workingList = list.slice()
    workingList.sort (a, b) ->
        # Sort by auth method name first
        if a.source < b.source
            return -1
        else if a.source > b.source
            return 1
        else
            # Sort Users above Groups if they have the same auth method
            if a.count? and not b.count?
                return 1
            else if not a.count? and b.count?
                return -1
            else
                # Sort by name if they're the same type as well
                if a.name < b.name
                    return -1
                else if a.name > b.name
                    return 1
                else
                    return 0
    return workingList


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
        sortEntities: sortEntities
    })
    return handlebars


exports.registerHelpers = registerHelpers

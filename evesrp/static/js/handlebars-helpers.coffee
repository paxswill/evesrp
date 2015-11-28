jQuery = require 'jquery'
Handlebars = require 'handlebars/runtime'
_ = require 'underscore'
capitalize = require 'underscore.string/capitalize'
sprintf = require 'underscore.string/sprintf'
util = require './util'
ui = require './common-ui'


csrf = () -> 
    token = jQuery "meta[name='csrf_token']"
    token.attr "content"


capitalizeHelper = (str) ->
    # TODO: I8N-ize, maybe?
    capitalize str


datefmt = (date) ->
    if typeof date == "string"
        date = new Date date
    ui.dateFormat.format date


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


registerHelpers = (handlebars) ->
    handlebars.registerHelper({
        csrf: csrf
        capitalize: capitalizeHelper
        datefmt: datefmt
        status_color: statusColor
        compare: compare
        count: count
        transformed: transformed
        gettext: gettext
    })
    return handlebars


exports.registerHelpers = registerHelpers

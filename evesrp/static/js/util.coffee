jQuery = require 'jquery'
_ = require 'underscore'
linkify = require 'linkifyjs/html'


exports.statusColor = (status) ->
    switch status
        when 'evaluating' then 'warning'
        when 'approved' then 'info'
        when 'paid' then 'success'
        when 'incomplete', 'rejected' then 'danger'
        else ''


exports.pageNumbers = (numPages, currentPage, options) ->
    # Set default options
    options = options ? {}
    leftEdge = options.leftEdge ? 2
    leftCurrent = options.leftCurrent ? 2
    rightCurrent = options.rightCurrent ? 5
    rightEdge = options.rightEdge ? 2

    pages = []
    for page in [1..numPages]
        if page <= leftEdge
            pages.push page
        else if (currentPage - leftCurrent) <= page < (currentPage + rightCurrent)
            pages.push page
        else if numPages - rightEdge < page
            pages.push page
        else if pages[pages.length - 1] != null
            pages.push null
    return pages


exports.localToUTC = (date) ->
    if typeof date == 'string'
        date = new Date date
    return new Date \
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds()


exports.urlize = (str, limit) ->
    if limit is undefined
        limit = Infinity
    return linkify str, {
        format: (value, type) ->
            if type == 'url' and value.length > limit
                value = "#{ value.slice 0, limit }..."
            return value
    }

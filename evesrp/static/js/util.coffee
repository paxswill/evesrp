jQuery = require 'jquery'
_ = require 'underscore'


exports.monthAbbr = (monthInt) ->
    switch monthInt
        when 0 then 'Jan'
        when 1 then 'Feb'
        when 2 then 'Mar'
        when 3 then 'Apr'
        when 4 then 'May'
        when 5 then 'Jun'
        when 6 then 'Jul'
        when 7 then 'Aug'
        when 8 then 'Sep'
        when 9 then 'Oct'
        when 10 then 'Nov'
        when 11 then 'Dec'


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


exports.getAttributeChoices = (attribute) ->
    if attribute == 'status'
        promise = jQuery.Deferred()
        promise.resolve {
            key: 'status'
            status: ['evaluating', 'approved', 'rejected', 'incomplete', 'paid']
        }
        return promise
    else if attribute in ['details', 'submit_timestamp', 'kill_timestamp']
        promise = jQuery.Deferred()
        promise.resolve {
            key: 'details'
            details: null
        }
        return promise
    else
        return jQuery.ajax {
            type: 'GET'
            url: "#{ $SCRIPT_ROOT }/api/filter/#{ attribute }/"
        }


exports.trimEmpty = (arrayOrObject) ->
    if _.isArray arrayOrObject
        array = arrayOrObject
        if array[0] == ''
            array = array[1..]
        if array[-1..][0] == ''
            array = array[...-1]
        return array
    else
        object = {}
        for key in _.keys arrayOrObject
            value = arrayOrObject[key]
            if _.isArray value
                if value.length != 0
                    object[key] = value
            else if _.isString value
                if value != ''
                    object[key] = value
            else unless _.isUndefined value
                object[key] = value
        return object


exports.splitFilterString = (pathname) ->
    # Split the navigation path from the query path. For example, when given
    # /requests/all/page/1/pilot/Paxswill/
    # This function will return ['requests/all', '/page/1/pilot/Paxswill']
    filterPath = pathname.split '/'
    filterPath = exports.trimEmpty(filterPath)
    knownAttributes = ['page', 'division', 'alliance', 'corporation', 'pilot',
                       'system', 'constellation', 'region', 'ship', 'status',
                       'details', 'sort', 'payout', 'base_payout',
                       'submit_timestamp', 'kill_timestamp']
    queryIndex = _.findIndex filterPath, ((entry) -> entry in knownAttributes)
    if queryIndex != -1
        [(filterPath[...queryIndex].join '/'),
         (filterPath[queryIndex..].join '/')]
    else
        [(filterPath.join '/'), '']


exports.parseFilterString = (filterString) ->
    # This is a straight port of the
    # evesrp.views.requests.RequestListing.parseFilterString function from
    # Python to Javascript.
    filters = {}
    # Default to these filters
    filters = _.defaults filters, {page: 1, sort: '-submit_timestamp'}
    # Fail fast for empty filters
    if filterString == undefined or filterString == ''
        return filters
    splitString = filterString.split '/'
    splitString = exports.trimEmpty splitString
    # Check for unpaired filters
    if splitString.length % 2 != 0
        return filters
    # CoffeeScript doesn't provide a basic for-loop, only a for-each
    i = 0
    while i < splitString.length
        # use toLowerCase to accept (erroneous) capitalized attribute names
        attr = splitString[i].toLowerCase()
        values = decodeURIComponent splitString[i + 1]
        # Prime the filters object with an empty array for each attribute
        unless attr of filters
            filters[attr] = []
        # Some attributes are special-cased
        switch attr
            when 'details'
                filters.details = _.union filters[attr], [values]
            when 'page'
                filters.page = parseInt values, 10
            when 'sort'
                filters.sort = values
            else
                if ',' in values
                    # Split comma-separated lists of values into arrays
                    values = values.split ','
                else
                    # Or turn single elements into an array
                    values = [values]
                filters[attr] = _.union filters[attr], values
        i += 2
    filters


exports.unParseFilters = (filters) ->
    # Like parseFilterString, this is a straight port of the
    # evesrp.views.requests.RequestListing.unparseFilters function from
    # Python to Javascript.
    filters = exports.trimEmpty filters
    keys = _.keys filters
    keys.sort()
    filterStrings = for attr in keys
        values = filters[attr]
        switch attr
            when 'details'
                details = for value in values
                    "details/#{ value }"
                details.join '/'
            when 'page', 'sort' then "#{ attr }/#{ values }"
            else
                values.sort()
                # TODO fix for values that contain commas
                values = values.join(',')
                "#{ attr }/#{ values }"
    filterStrings.join '/'


exports.keyDifference = (obj1, obj2) ->
    obj1 = exports.trimEmpty obj1
    obj2 = exports.trimEmpty obj2
    keys1 = _.keys obj1
    keys2 = _.keys obj2
    results = _.union (_.difference keys1, keys2), (_.difference keys2, keys1)
    for key in _.intersection keys1, keys2
        unless _.isEqual obj1[key], obj2[key]
            results.push key
    return results

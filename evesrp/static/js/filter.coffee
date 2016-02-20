jQuery = require 'jquery'
_ = require 'underscore'
require 'selectize'
ui = require 'evesrp/common-ui'
optionTemplate = require 'evesrp/templates/filter_option'
itemTemplate = require 'evesrp/templates/filter_item'
detailsTemplate = require 'evesrp/templates/filter_create'


getAttributeChoices = (attribute) ->
    if attribute == 'status'
        promise = jQuery.Deferred()
        promise.resolve {
            key: 'status'
            status: ['evaluating', 'approved', 'rejected', 'incomplete', 'paid']
        }
        return promise
    else if attribute in ['details', 'submit_timestamp', 'kill_timestamp']
        promise = jQuery.Deferred()
        data = { key: attribute }
        data[attribute] = null
        promise.resolve data
        return promise
    else
        return jQuery.ajax {
            type: 'GET'
            url: "#{ scriptRoot }/api/filter/#{ attribute }/"
        }


trimEmpty = (arrayOrObject) ->
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


keyDifference = (obj1, obj2) ->
    obj1 = trimEmpty obj1
    obj2 = trimEmpty obj2
    keys1 = _.keys obj1
    keys2 = _.keys obj2
    results = _.union (_.difference keys1, keys2), (_.difference keys2, keys1)
    for key in _.intersection keys1, keys2
        unless _.isEqual obj1[key], obj2[key]
            results.push key
    return results


splitFilterString = (pathname) ->
    # Split the navigation path from the query path. For example, when given
    # /requests/all/page/1/pilot/Paxswill/
    # This function will return ['requests/all', '/page/1/pilot/Paxswill']
    filterPath = pathname.split '/'
    filterPath = trimEmpty(filterPath)
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


parseFilterString = (filterString) ->
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
    splitString = trimEmpty splitString
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


unParseFilters = (filters) ->
    # Like parseFilterString, this is a straight port of the
    # evesrp.views.requests.RequestListing.unparseFilters function from
    # Python to Javascript.
    filters = trimEmpty filters
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


getFilters = () ->
    # Check for a history state object to use for the filters, falling back
    # to parsing the URL path
    unless _.isEmpty history.state?
        return history.state
    [basePath, filterPath] = splitFilterString window.location.pathname
    parseFilterString filterPath


updateURL = (filters) ->
    oldFilters = getFilters()
    # Double check that the filters have actually changed
    if _.isEqual oldFilters, filters
        return
    # Go to the first page when changing filters
    diffKeys = keyDifference oldFilters, filters
    unless 'page' in diffKeys
        filters.page = 1
    # Update URL bar and history
    [basePath, filterPath] = splitFilterString window.location.pathname
    filtersPath = unParseFilters filters
    history.pushState filters, null, "/#{ basePath }/#{ filtersPath }"
    # Update display
    (jQuery window).trigger 'evesrp:filterchange'


# This is a hack to not trigger events when messing with the items while
# responding to a popstate event
inPopState = false


createOption = (value, attribute, sign) ->
    # Helper function that creates an option for the selectize control (aka the
    # filter bar).
    translatedAttribute = ui.attributeGettext attribute
    {
        realValue: value
        attribute: attribute
        sign: sign
        display: "#{ translatedAttribute }:#{ sign }#{ value }"
    }


createFilterBar = (selector) ->
    attributes = [
        'pilot'
        'corporation'
        'alliance'
        'system'
        'constellation'
        'region'
        'ship'
        'status'
        'division'
        # These should probably be handled as a special case
        'details'
        'submit_timestamp'
        'kill_timestamp'
    ]
    itemsFromFilter = (filter) ->
        items = []
        for attribute in attributes
            if attribute of filter
                for value in filter[attribute]
                    translatedAttribute = ui.attributeGettext attribute
                    unless (value.charAt 0) in ['=', '-' , '<', '>']
                        items.push "#{ translatedAttribute }:=#{ value }"
                    else
                        items.push "#{ translatedAttribute }:#{ value }"
        return items
    ui.setupTranslations().done () ->
        items = itemsFromFilter getFilters()
        options = for item in items
            [match, attribute, sign, realValue] = /(\w+):([-=<>])(.*)/.exec item
            createOption realValue, attribute, sign
        $select = (jQuery selector).selectize {
            options: options
            items: items
            delimiter: ';'
            create: (input, callback) ->
                callback (createOption input, 'details', '=')
            # Note: if an option is added with addOption, it counts as a
            # user-defined option and will be removed if deselected, so we need
            # to have `persist` be true and remove old details searches
            # elsewhere.
            persist: true
            maxOptions: 20
            maxItems: null
            hideSelected: false
            openOnFocus: false
            closeAfterSelect: true
            dropdownParent: 'body'
            # Configure how to interpret/display data
            searchField: ['realValue', 'display']
            valueField: 'display'
            labelField: 'display'
            optgroups: {value: attr} for attr in attributes
            optgroupField: 'attribute'
            optgroupValueField: 'value'
            optgroupLabelField: 'value'
            render: {
                option: (data, cb) ->
                    optionTemplate data
                item: (data, cb) ->
                    itemTemplate data
                option_create: (data, cb) ->
                    detailsTemplate data
            }
            # Callbacks
            onChange: (value) ->
                null
            onItemAdd: (value, element) ->
                # If responding to a popstate event, skip processing
                if inPopState then return
                filters = getFilters()
                item = @options[value]
                unless item.attribute in filters
                    filters[item.attribute] = []
                # exact filters do not have any sign before them
                if item.sign == '='
                    filterString = item.realValue
                else
                    filterString = item.sign + item.realValue
                filters[item.attribute] = _.union filters[item.attribute],
                    [filterString]
                updateURL filters
            onItemRemove: (value) ->
                # If responding to a popstate event, skip processing
                if inPopState then return
                filters = getFilters()
                item = @options[value]
                if item.sign == '='
                    filterString = item.realValue
                else
                    filterString = item.sign + item.realValue
                filters[item.attribute] = _.without filters[item.attribute],
                    filterString
                # Remove details values from the list of options
                if item.attribute == 'details'
                    @removeOption value
                updateURL filters
            onDelete: (values) ->
                # This is a bit of a hack, but to prevent selectize from showing
                # the input when deleting, we're removing the items, but returning
                # false (cancelling the normal deletion process)
                while values.length
                    value = values.pop()
                    @removeItem value
                    if value in @options and @options[value].attribute == 'details'
                        @removeOption value
                false
        }
        selectize = $select[0].selectize
        # Add options for each attribute
        for attribute in attributes
            selectize.load (loadCB) ->
                attributePromise = getAttributeChoices attribute
                attributePromise.done (data) ->
                    options = []
                    key = data.key
                    values = data[key]
                    unless values == null
                        for value in values
                            # For now, status is the only exclusively exact
                            # filter.
                            unless key in ['status']
                                for sign in ['=', '-', '<', '>']
                                    options.push (createOption value, key, sign)
                            else
                                options.push (createOption value, key, '=')
                    loadCB options
        # Add an event handler for onpopstate so that the filter keeps updated when
        # using the forward/back buttons
        (jQuery window).on 'popstate', (ev) ->
            # jQuery wraps the event up
            if ev.originalEvent?
                state = ev.originalEvent.state
            else
                state = ev.state
            oldItems = selectize.items
            newItems = itemsFromFilter getFilters()
            toRemove = _.difference oldItems, newItems
            toAdd = _.difference newItems, oldItems
            # Set the flag to ignore selectize item events
            inPopState = true
            for item in toRemove
                selectize.removeItem item, true
                if item of selectize.options
                    data = selectize.options[item]
                    if data.attribute == 'details'
                        selectize.removeOption item
            for item in toAdd
                selectize.addItem item, true
            inPopState = false


# Private exports
exports._getAttributeChoices = getAttributeChoices
exports._trimEmpty = trimEmpty
exports._keyDifference = keyDifference
exports._splitFilterString = splitFilterString
# Public exports
exports.getFilters = getFilters
exports.unParseFilters = unParseFilters
exports.parseFilterString = parseFilterString
exports.updateURL = updateURL
exports.createFilterBar = createFilterBar

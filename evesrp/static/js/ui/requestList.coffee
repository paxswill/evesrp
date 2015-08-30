jQuery = require 'jquery'
_ = require 'underscore'
require 'selectize'
util = require '../util'
rowsTemplate = require '../templates/request_rows'
optionTemplate = require '../templates/filter_option'
itemTemplate = require '../templates/filter_item'


pageSize = 15


renderRequests = (data) ->
    $rows = (jQuery 'table#requests tr').not (jQuery '.popover tr')
    # Separate out the table headers and the data rows
    $headers = $rows.first().find 'th'
    $oldRows = $rows.not ':first'
    unless $oldRows.length == 0
        $oldRows.remove()
    # Figure out the column names
    columns = for header in $headers
        ((jQuery header).attr 'id')[4..]
    newRows = rowsTemplate data.requests
    $rows.parent().append newRows
    # Attach quick filtering listeners
    ($rows.parent().find '.filterable a').on 'click', addQuickFilter
    # Update summary footer
    $summary = jQuery '#requestsSummary'
    # TODO: i18n
    $summary.text "#{ data.request_count } requests •
                   #{ data.total_payouts } ISK"


renderPager = (data, filters) ->
    $pager = jQuery 'ul.pagination'
    numPages = (Math.ceil (data.request_count / pageSize - 1)) + 1
    $pager.empty
    if numPages > 1
        $pager.removeClass 'hidden'
        # Prev arrow
        if filters.page == 1
            $pager.append '<li class="disabled"><span>&laquo;</span></li>'
        else
            $pager.append '<li><a id="prev_page" href="#">&laquo;</a></li>'
        # Page numbers
        for pageNum in util.pageNumbers numPages, filters.page
            unless pageNum == null
                unless pageNum == filters.page
                    $pager.append "<li><a href=\"#\">#{ pageNum }
                                   </a></li>"
                else
                    # Highlight the current page number
                    $pager.append "<li class=\"active\">
                                   <a href=\"#\">#{ pageNum }
                                   <span class=\"sr-only\" (current)</span>
                                   </a></li>"
            else
                # null is the token for elided page numbers
                $pager.append '<li class="disabled"><span>&hellip;</span></li>'
        # Next arrow
        if filters.page == numPages
            $pager.append '<li class="disabled"><span>&raquo;</span></li>'
        else
            $pager.append '<li><a id="next_page" href="#">&raquo;</a></li>'
    else
        # Just hide the pager if there's only one page
        $pager.addClass 'hidden'


getFilters = () ->
    # Check for a history state object to use for the filters, falling back
    # to parsing the URL path
    unless _.isEmpty history.state?.data
        return history.state.data
    [basePath, filterPath] = util.splitFilterString window.location.pathname
    util.parseFilterString filterPath


getRequests = () ->
    urlPath = window.location.pathname
    jQuery.ajax {
        type: 'GET'
        url: urlPath
        success: (data) ->
            filters= getFilters()
            renderRequests data
            renderPager data, filters
    }


updateURL = (filters) ->
    oldFilters = getFilters()
    # Double check that the filters have actually changed
    if _.isEqual oldFilters, filters
        return
    # Go to the first page when changing filters
    diffKeys = util.keyDifference oldFilters, filters
    unless 'page' in diffKeys
        filters.page = 1
    # Update URL bar and history
    [basePath, filterPath] = util.splitFilterString window.location.pathname
    filtersPath = util.unParseFilters filters
    history.pushState filters, null, "/#{ basePath }/#{ filtersPath }"
    # Update display
    getRequests()


changeSort = (ev) ->
    $target = jQuery ev.target
    $targetHeader = $target.parent 'th'
    colName = ($targetHeader.attr 'id')[4..]
    # Fail fast for non-sortable columns
    if colName == 'None'
        return false
    # Determine the new sort
    # If the filters.sort == colName, just reverse the current sort
    # Otherwise, the new sort is colName
    filters = getFilters()
    if filters.sort == colName
        filters.sort = "-#{ colName }"
    else
        filters.sort = colName
    # Update sorting arrows
    $allHeaders = $targetHeader.parent().children 'th'
    ($allHeaders.find 'i.fa').removeClass()
    if (filters.sort.charAt 0) == '-'
        ($target.find 'i').addClass 'fa fa-chevron-down'
    else
        ($target.find 'i').addClass 'fa fa-chevron-up'
    updateURL(filters)
    false


changePage = (ev) ->
    $target = jQuery ev.target
    # Update the page number
    filters = getFilters()
    if ($target.attr 'id') == 'prev_page'
        filters.page -= 1
    else if ($target.attr 'id') == 'next_page'
        filters.page += 1
    else
        filters.page = parseInt $target.contents()[0].data, 10
    updateURL()
    false


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
    items = []
    filters = getFilters()
    for attribute in attributes
        if attribute of filters
            for value in filters[attribute]
                unless (value.charAt 0) in ['=', '-' , '<', '>']
                    items.push "#{ attribute }:=#{ value }"
                else
                    items.push "#{ attribute }:#{ value }"
    options = for item in items
        [match, attribute, sign, realValue] = /(\w+):([-=<>])(.*)/.exec item
        {
            realValue: realValue
            attribute: attribute
            sign: sign
            display: "#{ attribute }:#{ sign }#{ realValue }"
        }
    $select = (jQuery selector).selectize {
        options: options
        items: items
        delimiter: ';'
        create: true
        # Note: if an option is added with addOption, it counts as a
        # user-defined option and will be removed is deselected.
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
        }
        # Callbacks
        onChange: (value) ->
            null
        onItemAdd: (value, element) ->
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
            filters = getFilters()
            item = @options[value]
            if item.sign == '='
                filterString = item.realValue
            else
                filterString = item.sign + item.realValue
            filters[item.attribute] = _.without filters[item.attribute],
                filterString
            updateURL filters
    }
    selectize = $select[0].selectize
    for attribute in attributes
        selectize.load (loadCB) ->
            deferred = util.getAttributeChoices attribute
            deferred.done (data) ->
                options = []
                key = data.key
                values = data[key]
                unless values == null
                    for value in values
                        # For now, status is the only exclusively exact filter
                        unless key in ['status']
                            for sign in ['=', '-', '<', '>']
                                options.push {
                                    realValue: value
                                    attribute: key
                                    sign: sign
                                    display: "#{ key }:#{ sign }#{ value }"
                                }
                        else
                            options.push {
                                realValue: value
                                attribute: key
                                sign: '='
                                display: "#{ key }:=#{ value }"
                            }
                loadCB options



addQuickFilter = (ev) ->
    $cell = (jQuery ev.target).closest 'td'
    attribute = $cell.data 'attribute'
    value = $cell.text()
    if attribute == 'status'
        value = value.toLowerCase()
    selectize = (jQuery '.filter-tokenfield')[0].selectize
    selectize.addItem "#{ attribute }:=#{ value }", false
    false


setupEvents = () ->
    (jQuery 'th a.heading').on 'click', changeSort
    (jQuery 'ul.pagination').on 'click', changePage
    (jQuery '.filterable a').on 'click', addQuickFilter
    (jQuery window).on 'popstate', getRequests
    createFilterBar '.filter-tokenfield'


exports.setupEvents = setupEvents

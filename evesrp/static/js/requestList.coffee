jQuery = require 'jquery'
_ = require 'underscore'
capitalize = require 'underscore.string/capitalize'
sprintf = require 'underscore.string/sprintf'
util = require 'evesrp/util'
ui = require 'evesrp/common-ui'
filter = require 'evesrp/filter'
rowTemplate = require 'evesrp/templates/request_row'


pageSize = 15


renderRequests = (data) ->
    $rows = (jQuery 'table#requests tr').not (jQuery '.popover tr')
    $table = $rows.parent()
    formatsPromise = ui.setupFormats()
    # Separate out the table headers and the data rows
    $headers = $rows.first().find 'th'
    $oldRows = $rows.not ':first'
    # Figure out the column names
    columns = for header in $headers
        ((jQuery header).attr 'id')[4..]
    formatsPromise.done () ->
        unless $oldRows.length == 0
            $oldRows.remove()
        for request in data.requests
            statusColor = util.statusColor request.status
            $row = jQuery "<tr class=\"#{ statusColor }\"></tr>"
            for column in columns
                filterable = column in ['pilot', 'ship', 'system', 'status']
                value = switch column
                    when 'status' then capitalize request.status
                    when 'pilot', 'division' then request[column].name
                    when 'payout', 'base_payout'
                        currency = parseFloat request[column]
                        ui.currencyFormat currency
                    when 'submit_timestamp', 'kill_timestamp'
                        ui.dateFormatShort (util.localToUTC request[column])
                    else request[column]
                context = {
                    value: value
                    attribute: column
                    filterable: filterable
                }
                if column == 'id'
                    context.link = request.href
                $row.append rowTemplate context
            $table.append $row
        # Attach quick filtering listeners
        ($table.find '.filterable a').on 'click', addQuickFilter
    # Update summary footer
    $summary = jQuery '#requestsSummary'
    (jQuery.when formatsPromise, ui.setupTranslations()).done () ->
        request_count = ui.numberFormat data.request_count
        total_payouts = ui.currencyFormat (parseFloat data.total_payouts)
        requests_slug = ui.i18n.ngettext '%(num)s request', '%(num)s requests',
            data.request_count
        requests_text = sprintf requests_slug, { num: request_count }
        $summary.text "#{ requests_text } • #{ total_payouts } ISK"


renderPager = (data, currentFilters) ->
    $pager = jQuery 'ul.pagination'
    numPages = (Math.ceil (data.request_count / pageSize - 1)) + 1
    tempFilters = JSON.parse (JSON.stringify currentFilters)
    $pager.empty()
    if numPages > 1
        $pager.removeClass 'hidden'
        # Prev arrow
        if currentFilters.page == 1
            $pager.append '<li class="disabled"><span>&laquo;</span></li>'
        else
            tempFilters.page = currentFilters.page - 1
            newPath = filter.unParseFilters tempFilters
            $pager.append "<li><a id=\"prev_page\" href=\"#{ newPath }\">&laquo;</a></li>"
        # Page numbers
        for pageNum in util.pageNumbers numPages, currentFilters.page
            unless pageNum == null
                tempFilters.page = pageNum
                newPath = filter.unParseFilters tempFilters
                unless pageNum == currentFilters.page
                    $pager.append "<li><a href=\"#{ newPath }\">#{ pageNum }
                                   </a></li>"
                else
                    # Highlight the current page number
                    $pager.append "<li class=\"active\">
                                   <a href=\"#{ newPath }\">#{ pageNum }
                                   <span class=\"sr-only\" (current)</span>
                                   </a></li>"
            else
                # null is the token for elided page numbers
                $pager.append '<li class="disabled"><span>&hellip;</span></li>'
        # Next arrow
        if currentFilters.page == numPages
            $pager.append '<li class="disabled"><span>&raquo;</span></li>'
        else
            tempFilters.page = currentFilters.page + 1
            newPath = filter.unParseFilters tempFilters
            $pager.append "<li><a id=\"next_page\" href=\"#{ newPath }\">&raquo;</a></li>"
    else
        # Just hide the pager if there's only one page
        $pager.addClass 'hidden'


getRequests = () ->
    urlPath = window.location.pathname
    jQuery.ajax {
        type: 'GET'
        url: urlPath
        success: (data) ->
            filters = filter.getFilters()
            renderRequests data
            renderPager data, filters
    }


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
    filters = filter.getFilters()
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
    filter.updateURL filters
    false


addQuickFilter = (ev) ->
    $cell = (jQuery ev.target).closest 'td'
    attribute = $cell.data 'attribute'
    value = $cell.text()
    if attribute == 'status'
        value = value.toLowerCase()
    selectize = (jQuery '.filter-tokenfield')[0].selectize
    # Selectize keys options on their display value, so we ned to translate our
    # value for the current locale.
    ui.setupTranslations().done () ->
        translatedAttribute = ui.attributeGettext attribute
        selectize.addItem "#{ translatedAttribute }:=#{ value }", false
    false


setupEvents = () ->
    (jQuery 'th a.heading').on 'click', changeSort
    (jQuery '.filterable a').on 'click', addQuickFilter
    $window = jQuery window
    $window.on 'popstate', getRequests
    $window.on 'evesrp:filterchange', getRequests


exports.setupEvents = setupEvents

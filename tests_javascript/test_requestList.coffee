assert = require 'assert'
requestList = require 'evesrp/requestList'

suite 'Request Listings', () ->

    suite 'Rendering', () ->

        test 'Should remove old data from listing'

        test 'Should detect which columns are filterable'

        test 'Should add new rows from request data'

        test 'Should update the summary footer'

        suite 'Pager', () ->

            test 'Should hide the pager when there\'s only one page'

            test 'Should disable the back arrow only on the first page'

            test 'Should highlight only the current page'

            test 'Should render an ellipse for elided page numbers'

            test 'Should disable the forward arrow only on the first page'

            test 'Should go back one page when the back arrow is clicked'

            test 'Should go forwards one page when the forward arrow is clicked'

    suite 'Sorting', () ->

        test 'Should skip sorting by unsortable columns'

        test 'Should reverse the sort direction when clicking on the current sort'

        test 'Should display the correct chevron for the current sort'

    # aka Quick Filtering
    test 'Clicking an attribute should add a filter for that attribute'

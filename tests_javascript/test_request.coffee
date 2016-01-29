assert = require 'assert'
request = require 'evesrp/request'

suite 'Requests View', () ->

    suite 'Rendering', () ->

        test 'Should show a dropdown for possible actions besides comment'

        test 'Should skip the dropdown for possible actions if you can only comment'

        test 'Should show actions taken'

        test 'Should update the status badge'

        test 'Should render new modifiers'

        test 'Should show existing, voided modifiers as voided'

        test 'Should show voiding controls if user is able to voide modifiers'

        test 'Should update request details'

        test 'Should update the request division'

        test 'Should show the move divisions button if possible'

        # Make sure to test both the normal text and the tooltip
        test 'Should update the displayed and base payouts'

        test 'Should disable modifier and payout forms if request is not evaluating'

        test 'Should update links for existing transformed attributes'

    suite 'Actions', () ->

        test 'Should skip submitting when the dropdown toggle is clicked'

        test 'Should skip submitting when trying to comment with no text'

        test 'Should POST when the \'Comment\' button has been clicked'

        test 'Should POST when one of the dropdown actions has been clicked'

        test 'Should reset the dropdown on POST success'

        test 'Should update on POST success and failure'

    suite 'Modifiers', () ->

        test 'Should POST the new data when adding a modifier'

        test 'Should only reset the form when modifier added'

        test 'Should update on addition failure and success'

        test 'Should POST when voiding a modifier'

        test 'Should update on voiding failure and success'

    suite 'Payouts', () ->

        test 'Should POST new payout when button clicked'

        test 'Should clear payout form on success'

        test 'Should update for failure and success'

    test 'Should POST and hide modal when updating request details'

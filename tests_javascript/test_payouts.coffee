assert = require 'assert'
payouts = require 'evesrp/payouts'

suite 'Payout Mode', () ->

    suite 'Rendering', () ->

        test 'Should render an existing, expanded request'

        test 'Should render an existing, collapsed request'

        test 'Should render a new request'

        test 'Should re-attach clipboard event handlers'

    test 'Should send a POST when a request is marked as paid'

    suite 'Updating', () ->

        test 'Should not respect rate limit when refreshing from copy buttons'

        test 'Should load more requests as user scrolls down'

        test 'Should update existing requests when a user scrolls up or down'

        test 'Should respect rate limit when updating all requests'

        test 'Should ignore rate limit when updating a single request'

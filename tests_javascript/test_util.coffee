assert = require 'assert'
sinon = require 'sinon'
util = require 'evesrp/util'
math = require 'mathjs'

suite 'Utilities', () ->

    test 'Should return the Bootstrap color label for the given status', () ->
        assert.strictEqual (util.statusColor 'evaluating'), 'warning'
        assert.strictEqual (util.statusColor 'approved'), 'info'
        assert.strictEqual (util.statusColor 'paid'), 'success'
        assert.strictEqual (util.statusColor 'incomplete'), 'danger'
        assert.strictEqual (util.statusColor 'rejected'), 'danger'
        assert.strictEqual (util.statusColor 'foo'), ''

    test 'Should return a list of page numbers for the given options', () ->
        # This specific test case is taken from the Flask-SQLAlchemy test suite
        assert.deepEqual (util.pageNumbers 25, 1),
            [1, 2, 3, 4, 5, null, 24, 25]

    test 'Should convert a local Date to a UTC one', () ->
        now = new Date
        tzOffset = now.getTimezoneOffset()
        utcNow = util.localToUTC now
        hoursOffset = math.fix (tzOffset / 60)
        minutesOffset = tzOffset % 60
        assert.strictEqual utcNow.getHours() - hoursOffset, now.getHours()
        assert.strictEqual utcNow.getMinutes() - minutesOffset, now.getMinutes()

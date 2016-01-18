assert = require 'assert'
sinon = require 'sinon'
util = require '../evesrp/static/js/util'

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

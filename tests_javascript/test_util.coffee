assert = require 'assert'
sinon = require 'sinon'
_ = require 'underscore'
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

    test 'Should trim empty items in an array at the beginning and end', () ->
        assert.deepEqual (util.trimEmpty ['', 'foo', '']), ['foo']
        assert.deepEqual (util.trimEmpty ['foo', '']), ['foo']
        assert.deepEqual (util.trimEmpty ['', 'foo']), ['foo']
        assert.deepEqual (util.trimEmpty {foo: 'foo', bar: ''}), {foo: 'foo'}
        assert.deepEqual (util.trimEmpty {foo: 'foo', bar: ['bar']}),
            {foo: 'foo', bar: ['bar']}
        assert.deepEqual (util.trimEmpty {foo: 'foo', bar: []}), {foo: 'foo'}

    test 'Should split the query and location parts of the path apart', () ->
        assert.deepEqual (util.splitFilterString '/requests/all/page/1/'),
            ['requests/all', 'page/1']
        assert.deepEqual (util.splitFilterString \
                '/requests/all/page/1/pilot/Paxswill/'),
            ['requests/all', 'page/1/pilot/Paxswill']
        assert.deepEqual (util.splitFilterString \
                '/requests/all/page/1/pilot/Paxswill'),
            ['requests/all', 'page/1/pilot/Paxswill']
        assert.deepEqual (util.splitFilterString '/requests/all'),
            ['requests/all', '']
        assert.deepEqual (util.splitFilterString '/requests/all/'),
            ['requests/all', '']

    test 'Should parse the filter string into an object', () ->
        defaults = {page: 1, sort: '-submit_timestamp'}
        assert.deepEqual (util.parseFilterString ''), defaults
        assert.deepEqual (util.parseFilterString 'page/10/20'), defaults
        assert.deepEqual (util.parseFilterString 'page/10'),
            _.defaults {page: 10}, defaults
        assert.deepEqual (util.parseFilterString 'page/10/Pilot/Paxswill'),
            _.defaults {page: 10, pilot: ['Paxswill']}, defaults
        assert.deepEqual (util.parseFilterString \
            'page/10/pilot/Paxswill,DurrHurrDurr'),
            _.defaults {page: 10, pilot: ['Paxswill', 'DurrHurrDurr']}, defaults
        assert.deepEqual (util.parseFilterString \
            'details/Foo%20Bar%20Baz/'),
            _.defaults {page: 1, details: ["Foo Bar Baz"]}, defaults
        assert.deepEqual (util.parseFilterString 'PILOT/Paxswill'),
            _.defaults {pilot: ['Paxswill']}, defaults
        assert.deepEqual (util.parseFilterString \
            'pilot/Paxswill/pilot/DurrHurrDurr'),
            _.defaults {pilot: ['Paxswill', 'DurrHurrDurr']}, defaults

    test 'Should unparse a filters object into a filter string', () ->
        assert.strictEqual (util.unParseFilters {}), ''
        assert.strictEqual (util.unParseFilters {pilot: ['Paxswill']}),
            'pilot/Paxswill'
        assert.strictEqual (util.unParseFilters \
            {pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (util.unParseFilters \
            {system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (util.unParseFilters \
            {page: 42, system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'page/42/pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (util.unParseFilters {details: ['Foo Bar']}),
            'details/Foo Bar'
        assert.strictEqual (util.unParseFilters \
            {details: ['Foo Bar', 'Baz Qux']}),
            'details/Foo Bar/details/Baz Qux'

    test 'Should find the keys of two objects where they differ', () ->
        assert.deepEqual (util.keyDifference {a: '1'}, {b: '2'}), ['a', 'b']
        assert.deepEqual (util.keyDifference {a: '1'}, {a: '1'}), []
        assert.deepEqual (util.keyDifference {a: '1'}, {a: '2'}), ['a']
        assert.deepEqual (util.keyDifference \
            {a: '1', b: '2', d: '4'},
            {a: '1', c: '3', d: '4'}),
            ['b', 'c']

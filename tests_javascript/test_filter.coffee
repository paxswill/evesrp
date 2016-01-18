assert = require 'assert'
_ = require 'underscore'
filter = require '../evesrp/static/js/filter'

suite 'Filtering', () ->

    test.skip 'Should get choices for an attribute', () ->
        null

    test 'Should trim empty items in an array at the beginning and end', () ->
        assert.deepEqual (filter._trimEmpty ['', 'foo', '']), ['foo']
        assert.deepEqual (filter._trimEmpty ['foo', '']), ['foo']
        assert.deepEqual (filter._trimEmpty ['', 'foo']), ['foo']
        assert.deepEqual (filter._trimEmpty {foo: 'foo', bar: ''}), {foo: 'foo'}
        assert.deepEqual (filter._trimEmpty {foo: 'foo', bar: ['bar']}),
            {foo: 'foo', bar: ['bar']}
        assert.deepEqual (filter._trimEmpty {foo: 'foo', bar: []}), {foo: 'foo'}

    test 'Should find the keys of two objects where they differ', () ->
        assert.deepEqual (filter._keyDifference {a: '1'}, {b: '2'}), ['a', 'b']
        assert.deepEqual (filter._keyDifference {a: '1'}, {a: '1'}), []
        assert.deepEqual (filter._keyDifference {a: '1'}, {a: '2'}), ['a']
        assert.deepEqual (filter._keyDifference \
            {a: '1', b: '2', d: '4'},
            {a: '1', c: '3', d: '4'}),
            ['b', 'c']

    test 'Should split the query and location parts of the path apart', () ->
        assert.deepEqual (filter._splitFilterString '/requests/all/page/1/'),
            ['requests/all', 'page/1']
        assert.deepEqual (filter._splitFilterString \
                '/requests/all/page/1/pilot/Paxswill/'),
            ['requests/all', 'page/1/pilot/Paxswill']
        assert.deepEqual (filter._splitFilterString \
                '/requests/all/page/1/pilot/Paxswill'),
            ['requests/all', 'page/1/pilot/Paxswill']
        assert.deepEqual (filter._splitFilterString '/requests/all'),
            ['requests/all', '']
        assert.deepEqual (filter._splitFilterString '/requests/all/'),
            ['requests/all', '']

    test 'Should parse the filter string into an object', () ->
        defaults = {page: 1, sort: '-submit_timestamp'}
        assert.deepEqual (filter._parseFilterString ''), defaults
        assert.deepEqual (filter._parseFilterString 'page/10/20'), defaults
        assert.deepEqual (filter._parseFilterString 'page/10'),
            _.defaults {page: 10}, defaults
        assert.deepEqual (filter._parseFilterString 'page/10/Pilot/Paxswill'),
            _.defaults {page: 10, pilot: ['Paxswill']}, defaults
        assert.deepEqual (filter._parseFilterString \
            'page/10/pilot/Paxswill,DurrHurrDurr'),
            _.defaults {page: 10, pilot: ['Paxswill', 'DurrHurrDurr']}, defaults
        assert.deepEqual (filter._parseFilterString \
            'details/Foo%20Bar%20Baz/'),
            _.defaults {page: 1, details: ["Foo Bar Baz"]}, defaults
        assert.deepEqual (filter._parseFilterString 'PILOT/Paxswill'),
            _.defaults {pilot: ['Paxswill']}, defaults
        assert.deepEqual (filter._parseFilterString \
            'pilot/Paxswill/pilot/DurrHurrDurr'),
            _.defaults {pilot: ['Paxswill', 'DurrHurrDurr']}, defaults

    test 'Should unparse a filters object into a filter string', () ->
        assert.strictEqual (filter._unParseFilters {}), ''
        assert.strictEqual (filter._unParseFilters {pilot: ['Paxswill']}),
            'pilot/Paxswill'
        assert.strictEqual (filter._unParseFilters \
            {pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter._unParseFilters \
            {system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter._unParseFilters \
            {page: 42, system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'page/42/pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter._unParseFilters {details: ['Foo Bar']}),
            'details/Foo Bar'
        assert.strictEqual (filter._unParseFilters \
            {details: ['Foo Bar', 'Baz Qux']}),
            'details/Foo Bar/details/Baz Qux'

    test.skip 'Should get the current filters', () ->
        null

    test.skip 'Should update the URL and history for the current filters', () ->
        null

    test.skip 'Should create a translated Selectize option', () ->
        null

    test.skip 'Should create a filter bar using Selectize', () ->
        null

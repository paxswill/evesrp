assert = require 'assert'
_ = require 'underscore'
filter = require 'evesrp/filter'

suite 'Filtering', () ->

    test 'Should get the status choices for an attribute', () ->
        statusPromise = filter._getAttributeChoices 'status'
        statusPromise.done (data) ->
            assert.deepEqual data.status,
                ['evaluating', 'approved', 'rejected', 'incomplete', 'paid']
            assert.equal data.key, 'status'

    test 'Should get the null choices for an attribute', () ->
        for attr in ['details', 'submit_timestamp', 'kill_timestamp']
            promise = filter._getAttributeChoices attr
            promise.done (data) ->
                assert.equal data[attr], null
                assert.equal data.key, attr

    test 'Should trim empty items in an array at the beginning', () ->
        assert.deepEqual (filter._trimEmpty ['', 'foo', '']), ['foo']
        assert.deepEqual (filter._trimEmpty ['', 'foo']), ['foo']

    test 'Should trim empty items in an array at the end', () ->
        assert.deepEqual (filter._trimEmpty ['', 'foo', '']), ['foo']
        assert.deepEqual (filter._trimEmpty ['foo', '']), ['foo']

    test 'Should trim empty keys in an object', () ->
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

    test 'Should split an empty query path from the navigation path', () ->
        assert.deepEqual (filter._splitFilterString '/requests/all'),
            ['requests/all', '']
        assert.deepEqual (filter._splitFilterString '/requests/all/'),
            ['requests/all', '']

    test 'Should parse the filter string into an object', () ->
        defaults = {page: 1, sort: '-submit_timestamp'}
        assert.deepEqual (filter.parseFilterString ''), defaults
        assert.deepEqual (filter.parseFilterString 'page/10/20'), defaults
        assert.deepEqual (filter.parseFilterString 'page/10'),
            _.defaults {page: 10}, defaults
        assert.deepEqual (filter.parseFilterString 'page/10/Pilot/Paxswill'),
            _.defaults {page: 10, pilot: ['Paxswill']}, defaults
        assert.deepEqual (filter.parseFilterString \
            'page/10/pilot/Paxswill,DurrHurrDurr'),
            _.defaults {page: 10, pilot: ['Paxswill', 'DurrHurrDurr']}, defaults
        assert.deepEqual (filter.parseFilterString \
            'details/Foo%20Bar%20Baz/'),
            _.defaults {page: 1, details: ["Foo Bar Baz"]}, defaults
        assert.deepEqual (filter.parseFilterString 'PILOT/Paxswill'),
            _.defaults {pilot: ['Paxswill']}, defaults
        assert.deepEqual (filter.parseFilterString \
            'pilot/Paxswill/pilot/DurrHurrDurr'),
            _.defaults {pilot: ['Paxswill', 'DurrHurrDurr']}, defaults

    test 'Should unparse a filters object into a filter string', () ->
        assert.strictEqual (filter.unParseFilters {}), ''
        assert.strictEqual (filter.unParseFilters {pilot: ['Paxswill']}),
            'pilot/Paxswill'
        assert.strictEqual (filter.unParseFilters \
            {pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter.unParseFilters \
            {system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter.unParseFilters \
            {page: 42, system: [], pilot: ['Paxswill', 'DurrHurrDurr']}),
            'page/42/pilot/DurrHurrDurr,Paxswill'
        assert.strictEqual (filter.unParseFilters {details: ['Foo Bar']}),
            'details/Foo Bar'
        assert.strictEqual (filter.unParseFilters \
            {details: ['Foo Bar', 'Baz Qux']}),
            'details/Foo Bar/details/Baz Qux'

    suite.skip 'Creating filter live objects', () ->
        test 'Should check the history for a cached filter object'

        test 'Should create a new filter object from the current URL'

        test 'Should not update the URL for an unchanged filter'

        test 'Should reset the page to page 1 when changing the filters'

        test 'Should not reset the page when the page number is changing'

    test 'Should create a translated Selectize option'

    test 'Should create a filter bar using Selectize'

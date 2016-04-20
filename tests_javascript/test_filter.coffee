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

    defaultFilters = {page: 1, sort: '-submit_timestamp'}

    test 'Should parse the filter string into an object', () ->
        defaults = {page: 1, sort: '-submit_timestamp'}
        assert.deepEqual (filter._parseFilterString ''), defaultFilters
        assert.deepEqual (filter._parseFilterString 'page/10/20'),
            defaultFilters
        assert.deepEqual (filter._parseFilterString 'page/10'),
            _.defaults {page: 10}, defaultFilters
        assert.deepEqual (filter._parseFilterString 'page/10/Pilot/Paxswill'),
            _.defaults {page: 10, pilot: ['Paxswill']}, defaultFilters
        assert.deepEqual (filter._parseFilterString \
            'page/10/pilot/Paxswill,DurrHurrDurr'),
            _.defaults {page: 10, pilot: ['Paxswill', 'DurrHurrDurr']},
                defaultFilters
        assert.deepEqual (filter._parseFilterString \
            'details/Foo%20Bar%20Baz/'),
            _.defaults {page: 1, details: ["Foo Bar Baz"]}, defaultFilters
        assert.deepEqual (filter._parseFilterString 'PILOT/Paxswill'),
            _.defaults {pilot: ['Paxswill']}, defaultFilters
        assert.deepEqual (filter._parseFilterString \
            'pilot/Paxswill/pilot/DurrHurrDurr'),
            _.defaults {pilot: ['Paxswill', 'DurrHurrDurr']}, defaultFilters

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

    suite 'Creating filter objects', () ->
        # Note: I am not using Sinon for these functions as they make use of
        # window.history and window.location, which are special-cased in
        # browser implementations so you cannot (easily, if at all) stub them.
        # Manipulating the history is the easiest and simpliest method of
        # testing these functions I've found.

        suiteSetup () ->
            # Save the current location
            @originalLocation = window.location.href

        suiteTeardown () ->
            # Undo our history manipulations
            window.history.replaceState null, '', @originalLocation

        test 'Should check the history for a cached filter object', () ->
            window.history.replaceState {testing: true}, '', '/foo/bar'
            assert.deepEqual filter.getFilters(), {testing: true}

        test 'Should create a new filter object from the current URL', () ->
            window.history.replaceState null, '', '/'
            assert.deepEqual filter.getFilters(), defaultFilters
            window.history.replaceState null, '', '/requests/all/page/10'
            assert.deepEqual filter.getFilters(),
                (_.defaults {page: 10}, defaultFilters)

        test 'Should not update the URL for an unchanged filter', () ->
            startingPath = '/requests/all/page/10'
            startingFilter = {page: 10}
            window.history.replaceState startingFilter, '', startingPath
            filter.updateURL {page: 10}
            assert.strictEqual window.location.pathname, startingPath
            assert.deepEqual history.state, startingFilter

        test 'Should reset the page to page 1 when changing the filters', () ->
            window.history.replaceState {page: 10}, '', '/requests/all/page/10'
            filter.updateURL {pilot: ['Paxswill'], page: 10}
            assert.deepEqual history.state, {pilot: ['Paxswill'], page: 1}
            assert.strictEqual window.location.pathname,
                '/requests/all/page/1/pilot/Paxswill'

        test 'Should not reset the page when the page number is changing', () ->
            window.history.replaceState {page: 10}, '', '/requests/all/page/10'
            filter.updateURL {page: 11}
            assert.deepEqual history.state, {page: 11}
            assert.strictEqual window.location.pathname, '/requests/all/page/11'

    test 'Should create a translated Selectize option'

    test 'Should create a filter bar using Selectize'

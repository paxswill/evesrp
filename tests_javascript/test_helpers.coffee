assert = require 'assert'
sinon = require 'sinon'
Handlebars = require 'handlebars'
# Pile of JSON files normally fetched from the server.
enTranslation = require 'evesrp/translations/en-US.json'
likelySubtags = require 'cldr-data/supplemental/likelySubtags.json'
enGregorian = require 'cldr-dates-full/main/en/ca-gregorian.json'
tzNames = require 'cldr-dates-full/main/en/timeZoneNames.json'
numbers = require 'cldr-numbers-full/main/en/numbers.json'
numberingSystems = require 'cldr-data/supplemental/numberingSystems.json'
timeData = require 'cldr-data/supplemental/timeData.json'
weekData = require 'cldr-data/supplemental/weekData.json'


suite 'Handlebars Helpers', () ->

    suiteSetup () ->
        @server = sinon.fakeServer.create()
        @server.respondImmediately = true
        global.scriptRoot = ''
        cldrRoot = '/static/cldr'
        urls = {
            '/static/translations/en-US.json': enTranslation
            "#{ cldrRoot }/supplemental/likelySubtags.json": likelySubtags
            "#{ cldrRoot }/main/en/ca-gregorian.json": enGregorian
            "#{ cldrRoot }/main/en/timeZoneNames.json": tzNames
            "#{ cldrRoot }/main/en/numbers.json": numbers
            "#{ cldrRoot }/supplemental/numberingSystems.json": numberingSystems
            "#{ cldrRoot }/supplemental/timeData.json": timeData
            "#{ cldrRoot }/supplemental/weekData.json": weekData
        }
        for url, obj of urls
            @server.respondWith 'GET', url,
                [
                    200,
                    {'Content-Type': 'application/json'},
                    JSON.stringify obj,
                ]
        registerHelpers = (require 'evesrp/handlebars-helpers').registerHelpers
        registerHelpers(Handlebars)

    suiteTeardown () ->
        @server.restore()

    test 'Should capitalize the first letter in a word', () ->
        template = Handlebars.compile '{{capitalize foo}}'
        assert.strictEqual template({foo: 'foo'}), 'Foo'
        assert.strictEqual template({foo: 'Foo'}), 'Foo'
        assert.strictEqual template({foo: ' foo'}), ' foo'
        assert.strictEqual template({foo: ' Foo'}), ' Foo'

    test 'Should format a date', () ->
        @timeout(10000)
        # Set a language before importing common-ui and setting up the
        # translations
        document.documentElement.lang = 'en-US'
        ui = require 'evesrp/common-ui'
        ui.setupTranslations().done () ->
            mediumTemplate = Handlebars.compile '{{datefmt date}}'
            assert.strictEqual mediumTemplate({date: '2015-08-24T00:00Z'}),
                'Aug 24, 2015, 12:00:00 AM'
            assert.strictEqual mediumTemplate({date: '2015-12-03T00:00Z'}),
                'Dec 3, 2015, 12:00:00 AM'
            assert.strictEqual mediumTemplate({date: '2015-01-24T00:00Z'}),
                'Jan 24, 2015, 12:00:00 AM'
            assert.strictEqual mediumTemplate({date: '2015-05-01T00:00Z'}),
                'May 1, 2015, 12:00:00 AM'
            shortTemplate = Handlebars.compile "{{datefmt date style='short'}}"
            assert.strictEqual shortTemplate({date: '2015-08-24T00:00Z'}),
                '8/24/15, 12:00 AM'
            assert.strictEqual shortTemplate({date: '2015-12-03T00:00Z'}),
                '12/3/15, 12:00 AM'
            assert.strictEqual shortTemplate({date: '2015-01-24T00:00Z'}),
                '1/24/15, 12:00 AM'
            assert.strictEqual shortTemplate({date: '2015-05-01T00:00Z'}),
                '5/1/15, 12:00 AM'

    test 'Should display a Bootstrap color class for a status', () ->
        template = Handlebars.compile '{{status_color status}}'
        assert.strictEqual template({status: 'evaluating'}), 'warning'

    test 'Should perform rich comparisons in templates', () ->
        # these templates return A for true and B for false
        templates = {}
        for op in ['==', '===', '!=' ,'!==', '<', '>', '<=', '>=', 'in', 'of']
            metaTemplate = \
                "{{#compare a b operator='#{ op }'}}A{{else}}B{{/compare}}"
            templates[op] = Handlebars.compile metaTemplate
        templates[''] = Handlebars.compile \
            "{{#compare a b}}A{{else}}B{{/compare}}"
        # Equality
        assert.strictEqual templates['']({a: 1, b: 1}), 'A'
        assert.strictEqual templates['']({a: 1, b: 2}), 'B'
        assert.strictEqual templates['==']({a: 1, b: 1}), 'A'
        assert.strictEqual templates['==']({a: 1, b: 2}), 'B'
        assert.strictEqual templates['===']({a: 1, b: 1}), 'A'
        assert.strictEqual templates['===']({a: 1, b: 2}), 'B'
        # Inequality
        assert.strictEqual templates['!=']({a: 1, b: 1}), 'B'
        assert.strictEqual templates['!=']({a: 1, b: 2}), 'A'
        assert.strictEqual templates['!==']({a: 1, b: 1}), 'B'
        assert.strictEqual templates['!==']({a: 1, b: 2}), 'A'
        # Less + Less than or equal
        assert.strictEqual templates['<']({a: 1, b: 1}), 'B'
        assert.strictEqual templates['<']({a: 1, b: 2}), 'A'
        assert.strictEqual templates['<']({a: 2, b: 1}), 'B'
        assert.strictEqual templates['<=']({a: 1, b: 1}), 'A'
        assert.strictEqual templates['<=']({a: 1, b: 2}), 'A'
        assert.strictEqual templates['<=']({a: 2, b: 1}), 'B'
        # Greater + Greater than or Equal
        assert.strictEqual templates['>']({a: 1, b: 1}), 'B'
        assert.strictEqual templates['>']({a: 1, b: 2}), 'B'
        assert.strictEqual templates['>']({a: 2, b: 1}), 'A'
        assert.strictEqual templates['>=']({a: 1, b: 1}), 'A'
        assert.strictEqual templates['>=']({a: 1, b: 2}), 'B'
        assert.strictEqual templates['>=']({a: 2, b: 1}), 'A'
        # Arrays and Strings
        assert.strictEqual templates['in']({a: 'b', b: ['a', 'b', 'c']}), 'A'
        assert.strictEqual templates['in']({a: 'z', b: ['a', 'b', 'c']}), 'B'
        assert.strictEqual templates['in']({a: 'b', b: 'abc'}), 'A'
        assert.strictEqual templates['in']({a: 'z', b: 'abc'}), 'B'
        # Objects
        assert.strictEqual templates['of']({a: 'foo', b: {foo: 1, bar:2}}), 'A'
        assert.strictEqual templates['of']({a: 'baz', b: {foo: 1, bar:2}}), 'B'

    test 'Should count the elements in an array', () ->
        template = Handlebars.compile "{{count a}}"
        assert.strictEqual (template {a: ['1', '2', '3']}), '3'
        assert.strictEqual (template {a: []}), '0'

    test 'Should look up a URL for an attribute', () ->
        template = Handlebars.compile "{{transformed request attr}}"
        request =
            pilot: 'Paxswill'
            ship: 'Guardian'
            transformed:
                pilot: 'http://evewho.com/pilot/Paxswill'
        assert.strictEqual (template {request: request, attr: 'pilot'}),
            '<a href="http://evewho.com/pilot/Paxswill" target="_blank">Paxswill
             <i class="fa fa-external-link"></i></a>'
        assert.strictEqual (template {request: request, attr: 'ship'}),
            'Guardian'

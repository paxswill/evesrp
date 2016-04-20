assert = require 'assert'
sinon = require 'sinon'
ui = require 'evesrp/common-ui'

suite 'Common UI', () ->

    suiteSetup () ->
        @sandbox = sinon.sandbox.create()
        @sandbox.useFakeServer()
        @sandbox.useFakeTimers()
        @sandbox.server.respondImmediately = true
        global.scriptRoot = ''

        fixtures = jQuery '#fixtures'
        @fixture = jQuery '<div id="common-ui-fixtures"></div>'
        @languageFixture = @fixture.append """
        <form method="GET">
          <input id="lang" type="hidden" name="lang" value="">
          <a class="langSelect" data-lang="es" href="#">Español</a>
          <a class="langSelect" data-lang="de" href="#">Deutsch</a>
        </form>
        """
        @flashesFixture = @fixture.append """<div id="content"></div>"""
        @navBarFixture = @fixture.append """
        <div id="badge-pending"></div>
        <div id="badge-payouts"></div>
        <div id="badge-personal"></div>
        """
        fixtures.append @fixture
        ui.setupEvents()

    suiteTeardown () ->
        @sandbox.restore()
        @fixture.remove()

    test 'Should set a new language'

    test 'Should render a flash', () ->
        @sandbox.server.respondWith [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {flashed_messages: [
                {message: 'Testing1', category: 'warning'}
            ]}
        ]
        jQuery.get '/'
        alerts = @flashesFixture.find '.alert'
        assert.strictEqual alerts.length, 1
        assert.ok (alerts[0].innerText.indexOf 'Testing1') != -1
        @sandbox.clock.tick 2500
        @sandbox.server.respondWith [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {flashed_messages: [
                {message: 'Testing2', category: 'message'}
            ]}
        ]
        jQuery.get '/'
        alerts = @flashesFixture.find '.alert'
        assert.strictEqual alerts.length, 2
        @sandbox.clock.tick 3000
        alerts = @flashesFixture.find '.alert'
        assert.strictEqual alerts.length, 1
        @sandbox.clock.tick 3000
        alerts = @flashesFixture.find '.alert'
        assert.strictEqual alerts.length, 0


    test 'Should update item counts in the navbar', () ->
        @sandbox.server.respondWith [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {nav_counts: {pending: 2, payouts: 4, personal: 6}}
        ]
        jQuery.get '/'
        assert.strictEqual (@navBarFixture.find '#badge-pending').text(), '2'
        assert.strictEqual (@navBarFixture.find '#badge-payouts').text(), '4'
        assert.strictEqual (@navBarFixture.find '#badge-personal').text(), '6'
        @sandbox.server.respondWith [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {nav_counts: {pending: 2, payouts: 0, personal: 6}}
        ]
        jQuery.get '/'
        assert.strictEqual (@navBarFixture.find '#badge-payouts').text(), ''

    suite 'Localization', () ->

        test 'Should retrieve translation files for the current locale'

        test 'Should return the existing promise for an in-progress setup'

        test 'Should translate strings to the current locale'

        test 'Should format currency for ISK for the current locale'

        test 'Should format percentages for the current locale'

        test 'Should format decimal numbers for the current locale'

        test 'Should format dates in a short format for the current locale'

        test 'Should format dates in a medium format for the current locale'

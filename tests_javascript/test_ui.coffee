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
        @languageFixture = jQuery """
        <form method="GET">
          <input id="lang" type="hidden" name="lang" value="">
          <a class="langSelect" data-lang="es" href="#">Español</a>
        </form>
        """
        @flashesFixture = jQuery """<div id="content"></div>"""
        @navBarFixture = jQuery """
        <div id="badge-pending">1</div>
        <div id="badge-payouts">3</div>
        <div id="badge-personal">5</div>
        """
        @fixture.append @languageFixture
        @fixture.append @flashesFixture
        @fixture.append @navBarFixture
        fixtures.append @fixture
        ui.setupEvents()

    suiteTeardown () ->
        @sandbox.restore()
        @fixture.remove()

    test 'Should set a new language', () ->
        submitSpy = @sandbox.stub jQuery.prototype, 'submit'
        @languageFixture.find('a').click()
        sinon.assert.calledOnce submitSpy
        assert.strictEqual (submitSpy.firstCall.thisValue.find '#lang').val(),
            'es'

    test 'Should render a flash', () ->
        @sandbox.server.respondWith '/flash-test1', [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {flashed_messages: [
                {message: 'Testing1', category: 'warning'}
            ]}
        ]
        jQuery.get '/flash-test1'
        alerts = @fixture.find '.alert'
        assert.strictEqual alerts.length, 1
        assert.ok (alerts[0].innerText.indexOf 'Testing1') != -1
        @sandbox.clock.tick 2500
        @sandbox.server.respondWith '/flash-test2', [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {flashed_messages: [
                {message: 'Testing2', category: 'message'}
            ]}
        ]
        jQuery.get '/flash-test2'
        alerts = @fixture.find '.alert'
        assert.strictEqual alerts.length, 2
        @sandbox.clock.tick 3000
        alerts = @fixture.find '.alert'
        assert.strictEqual alerts.length, 1
        @sandbox.clock.tick 3000
        alerts = @fixture.find '.alert'
        assert.strictEqual alerts.length, 0


    test 'Should update item counts in the navbar', () ->
        @sandbox.server.respondWith '/navbar-test1', [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {nav_counts: {pending: 2, payouts: 4, personal: 6}}
        ]
        jQuery.get '/navbar-test1'
        assert.strictEqual (@fixture.find '#badge-pending').text(), '2'
        assert.strictEqual (@fixture.find '#badge-payouts').text(), '4'
        assert.strictEqual (@fixture.find '#badge-personal').text(), '6'

    test 'Should clear item counts in navbar for 0', () ->
        @sandbox.server.respondWith '/navbar-test2', [
            200
            {'Content-Type': 'application/json'}
            JSON.stringify {nav_counts: {pending: 2, payouts: 0, personal: 6}}
        ]
        jQuery.get '/navbar-test2'
        assert.strictEqual (@fixture.find '#badge-payouts').text(), ''

    suite 'Localization', () ->

        test 'Should retrieve translation files for the current locale'

        test 'Should return the existing promise for an in-progress setup'

        test 'Should translate strings to the current locale'

        test 'Should format currency for ISK for the current locale'

        test 'Should format percentages for the current locale'

        test 'Should format decimal numbers for the current locale'

        test 'Should format dates in a short format for the current locale'

        test 'Should format dates in a medium format for the current locale'

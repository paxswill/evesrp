assert = require 'assert'
apiKeys = require 'evesrp/apiKeys'

suite 'API Keys', () ->

    suite 'Rendering', () ->

        test 'Should render a new API key with no pre-existing keys'

        test 'Should render a new API key with pre-existing keys'

        test 'Should render removing an API key leaving no keys'

        test 'Should render removing an API key leaving other keys'

    suite 'POSTing', () ->

        test 'Should POST adding a key, with a positive response'

        test 'Should POST removing a key, with a positive response'

        test 'Should POST adding a key, with a server-side failure'

        test 'Should POST removing a key, with a server-side failure'

assert = require 'assert'
division = require 'evesrp/division'

suite 'Division UI', () ->

    test 'Should render all entities in a division'

    suite 'Transformers', () ->

        test 'Should GET the list of transformers for an attribute'

        test 'Should set the list transformer choices for an attribute'

        test 'Should POST a newly selected attribute'

    suite 'Entity Selection', () ->

        test 'Should create a Selectize instance on a given selector'

        test 'Should separate entites by type'

        test 'Should POST the selection of an entity'

        test 'Should render users'

        test 'Should render groups'

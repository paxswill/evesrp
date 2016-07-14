import pytest
from httmock import HTTMock
from evesrp import ships


def test_known_ship_type():
    assert ships.ships[587] == 'Rifter'


def test_unknown_ship_type(evesrp_app, crest):
    # Tested within a context so the dynamic lookup capability has access
    # to a requests session.
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert ships.ships[123456789] == 'Svipul'


def test_invalid_id(evesrp_app, crest):
    # Check what happens when you pass in strings or whatever
    with pytest.raises(TypeError):
        ships.ships['Svipul']
    # Check for invalid typeIDs
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            with pytest.raises(KeyError):
                ships.ships[999999999]

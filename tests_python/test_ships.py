import pytest
from httmock import HTTMock
from evesrp import ships


@urlmatch(scheme='https',
          netloc=r'crest-tq\.eveonline\.com',
          path=r'^/?$')
def crest_root(url, request):
    resp = {
        'itemTypes': {
            'href': 'https://crest-tq.eveonline.com/types/',
        },
    }
    return response(content=json.dumps(resp))


# Using a purposely invalid typeID to ensure we hit HTTMock
@urlmatch(scheme='https',
          netloc=r'crest-tq\.eveonline\.com',
          path=r'^/types/123456789/$')
def _svipul_lookup(url, request):
    resp = {
        'name': 'Svipul',
        'description': 'Stuff about being released in YC 117.',
    }
    return response(content=json.dumps(resp))
svipul_lookup = [crest_root, _svipul_lookup]


@urlmatch(scheme='https',
          netloc=r'crest-tq\.eveonline\.com',
          path=r'^/types/999999999/$')
def _invalid_lookup(url, request):
    resp = """{'message': 'Type not found',
        'key': 'typeNotFound',
        'exceptionType': 'NotFoundError'}"""
    return response(status_code=404, content=resp)
invalid_lookup = [crest_root, _invalid_lookup]


def test_known_ship_type():
    assert ships.ships[587] == 'Rifter'


def test_unknown_ship_type(evesrp_app):
    # Tested within a context so the dynamic lookup capability has access
    # to a requests session.
    with evesrp_app.test_request_context():
        with HTTMock(*svipul_lookup):
            assert ships.ships[123456789] == 'Svipul'


def test_invalid_id(evesrp_app):
    # Check what happens when you pass in strings or whatever
    with pytest.raises(TypeError):
        ships.ships['Svipul']
    # Check for invalid typeIDs
    with evesrp_app.test_request_context():
        with HTTMock(*invalid_lookup):
            with pytest.raises(KeyError):
                ships.ships[999999999]

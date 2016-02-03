import json
from six.moves.urllib.parse import urlparse
from httmock import HTTMock, urlmatch
from .util_tests import TestApp, response
from evesrp import ships


# Using a purposely invalid typeID to ensure we hit HTTMock
_parsed_svipul = urlparse(
        'https://public-crest.eveonline.com/types/123456789/')
@urlmatch(scheme=_parsed_svipul.scheme,
          netloc=_parsed_svipul.netloc,
          path=_parsed_svipul.path)
def svipul_lookup(url, request):
    resp = {
        'name': 'Svipul',
        'description': 'Stuff about being released in YC 117.',
    }
    return response(content=json.dumps(resp))


_parsed_invalid = urlparse(
        'https://public-crest.eveonline.com/types/999999999/')
@urlmatch(scheme=_parsed_invalid.scheme,
          netloc=_parsed_invalid.netloc,
          path=_parsed_invalid.path)
def invalid_lookup(url, request):
    resp = """{'message': 'Type not found',
        'key': 'typeNotFound',
        'exceptionType': 'NotFoundError'}"""
    return response(status_code=404, content=resp)


class TestShipLookup(TestApp):

    def test_known(self):
        self.assertEqual(ships.ships[587], 'Rifter')

    def test_unknown(self):
        with self.app.test_request_context():
            with HTTMock(svipul_lookup):
                self.assertEqual(ships.ships[123456789], 'Svipul')

    def test_invalid_id(self):
        # Check what happens when you pass in strings or whatever
        with self.assertRaises(TypeError):
            ships.ships['Svipul']
        # Check for invalid typeIDs
        with self.app.test_request_context():
            with HTTMock(invalid_lookup):
                with self.assertRaises(KeyError):
                    ships.ships[999999999]

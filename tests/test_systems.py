import json
from six.moves.urllib.parse import urlparse
from httmock import HTTMock, urlmatch
from .util_tests import TestApp, response
from evesrp import systems


# Prefixing all ID numbers with 999 to force them to not be found in the
# packaged info.
@urlmatch(scheme='https',
          netloc=r'(public-)?crest(-tq)?\.eveonline\.com',
          path=r'^/solarsystems/(999)?30000142/$')
def jita_lookup(url, request):
    resp = {
        'name': 'Jita',
        # The "internal" crest links aren't prefixed, as those are used for
        # system->constellation and constellation->region lookups
        'constellation': {'href':
            'https://public-crest.eveonline.com/constellations/20000020/'},
    }
    return response(content=json.dumps(resp))


@urlmatch(scheme='https',
          netloc=r'(public-)?crest(-tq)?\.eveonline\.com',
          path=r'^/constellations/(999)?20000020/$')
def kimotoro_lookup(url, request):
    resp = {
        'name': 'Kimotoro',
        'region': {'href':
            'https://public-crest.eveonline.com/regions/10000002/'},
    }
    return response(content=json.dumps(resp))


@urlmatch(scheme='https',
          netloc=r'(public-)?crest(-tq)?\.eveonline\.com',
          path=r'^/regions/(999)?10000002/$')
def forge_lookup(url, request):
    resp = {
        'name': 'The Forge',
    }
    return response(content=json.dumps(resp))


class TestLocationLookup(TestApp):

    def test_system_name(self):
        with self.app.test_request_context():
            with HTTMock(jita_lookup):
                self.assertEqual(systems.system_names[99930000142], 'Jita')

    def test_constellation_name(self):
        with self.app.test_request_context():
            with HTTMock(kimotoro_lookup):
                self.assertEqual(systems.constellation_names[99920000020],
                        'Kimotoro')

    def test_region_name(self):
        with self.app.test_request_context():
            with HTTMock(forge_lookup):
                self.assertEqual(systems.region_names[99910000002], 'The Forge')

    def test_systems_constellations(self):
        with self.app.test_request_context():
            with HTTMock(jita_lookup, kimotoro_lookup):
                self.assertEqual(systems.systems_constellations[99930000142],
                        20000020)

    def test_constellations_regions(self):
        with self.app.test_request_context():
            with HTTMock(kimotoro_lookup, forge_lookup):
                self.assertEqual(systems.constellations_regions[99920000020],
                        10000002)

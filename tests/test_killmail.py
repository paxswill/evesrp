from unittest import TestCase
from httmock import HTTMock, all_requests
from evesrp import killmail
from .util import all_mocks, response


class TestKillmail(TestCase):

    def test_default_values(self):
        km = killmail.Killmail()
        attrs = ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
            'corp_id', 'corp', 'alliance_id', 'alliance', 'verified',
            'url', 'value', 'timestamp', 'system', 'constellation',
            'region')
        for attr in attrs:
            self.assertIsNone(getattr(km, attr))

    def test_hidden_data(self):
        km = killmail.Killmail()
        old_dir = dir(km)
        km.foo = 'bar'
        new_dir = dir(km)
        self.assertEqual(old_dir, new_dir)
        self.assertIn('foo', km._data)
        self.assertEqual(km.foo, 'bar')

    def test_keyword_arguments(self):
        km = killmail.Killmail(kill_id=123456)
        self.assertEqual(km.kill_id, 123456)


class TestNameMixin(TestCase):

    def setUp(self):
        self.NameMixed = type('NameMixed', (killmail.Killmail,
                killmail.ShipNameMixin), dict())

    def test_devoter_id(self):
        km = self.NameMixed(ship_id=12017)
        self.assertEqual(km.ship, 'Devoter')


class TestLocationMixin(TestCase):

    def setUp(self):
        self.LocationMixed = type('LocationMixed', (killmail.Killmail,
                killmail.LocationMixin), dict())

    def test_system(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.system, 'Jita')

    def test_constellation(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.constellation, 'Kimotoro')

    def test_region(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.region, 'The Forge')


class TestRequestsMixin(TestCase):

    def setUp(self):
        self.SessionMixed = type('SessionMixed', (killmail.Killmail,
                killmail.RequestsSessionMixin), dict())

    def test_default_creation(self):
        km = self.SessionMixed()
        self.assertIsNotNone(km.requests_session)

    def test_provided_session(self):
        session = object()
        km = self.SessionMixed(requests_session=session)
        self.assertIs(km.requests_session, session)


class TestZKillmail(TestCase):

    def test_fw_killmail(self):
        with HTTMock(*all_mocks):
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/37637533/')
            expected_values = {
                'pilot': 'Paxswill',
                'ship': 'Devoter',
                'corp': 'Dreddit',
                'alliance': 'Test Alliance Please Ignore',
                'system': 'TA3T-3',
                'domain': 'zkillboard.com'
            }
            for attr, value in expected_values.items():
                self.assertEqual(getattr(km, attr), value,
                        msg='{} is not {}'.format(attr, value))

    def test_no_alliance_killmail(self):
        with HTTMock(*all_mocks):
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/38862043/')
            expected_values = {
                'pilot': 'Dave Duclas',
                'ship': 'Breacher',
                'corp': 'Omega LLC',
                'alliance': None,
                'system': 'Onatoh',
                'domain': 'zkillboard.com'
            }
            for attr, value in expected_values.items():
                self.assertEqual(getattr(km, attr), value,
                        msg='{} is not {}'.format(attr, value))

    def test_invalid_zkb_url(self):
        with self.assertRaisesRegexp(ValueError,
                "'.*' is not a valid zKillboard killmail"):
            killmail.ZKillmail('foobar')

    def test_invalid_zkb_response(self):
        @all_requests
        def bad_response(url, request):
            return response(status_code=403, content='')

        with HTTMock(bad_response):
            url = 'https://zkillboard.com/kill/38862043/'
            with self.assertRaisesRegexp(LookupError,
                    "Error retrieving killmail data:.*"):
                killmail.ZKillmail(url)

    def test_invalid_kill_ids(self):
        @all_requests
        def empty_response(url, request):
            return response(content='[]')

        with HTTMock(empty_response):
            url = 'https://zkillboard.com/kill/0/'
            with self.assertRaisesRegexp(LookupError, "Invalid killmail: .*"):
                killmail.ZKillmail(url)


class TestCRESTmail(TestCase):

    def test_crest_killmails(self):
        with HTTMock(*all_mocks):
            km = killmail.CRESTMail('http://public-crest.eveonline.com/'
                    'killmails/30290604/'
                    '787fb3714062f1700560d4a83ce32c67640b1797/')
            expected_values = {
                'pilot': 'CCP FoxFour',
                'ship': 'Capsule',
                'corp': 'C C P',
                'alliance': 'C C P Alliance',
                'system': 'Todifrauan',
            }
            for attr, value in expected_values.items():
                self.assertEqual(getattr(km, attr), value,
                        msg='{} is not {}'.format(attr, value))

    def test_invalid_crest_url(self):
        with self.assertRaisesRegexp(ValueError,
                "'.*' is not a valid CREST killmail"):
            killmail.CRESTMail('foobar')

    def test_invalid_crest_response(self):
        @all_requests
        def bad_hash(url, request):
            return response(
                content=('{"message": "Invalid killmail ID or hash",'
                        '"isLocalized": false, "key": "noSuchKill",'
                        '"exceptionType": "ForbiddenError"}').encode('utf-8'),
                status_code=403)

        with HTTMock(bad_hash):
            url = ''.join(('http://public-crest.eveonline.com/killmails/',
                    '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'))
            with self.assertRaisesRegexp(LookupError,
                    "Error retrieving CREST killmail:.*"):
                killmail.CRESTMail(url)

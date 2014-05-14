from unittest import TestCase
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock

from evesrp import killmail


class TestKillmail(TestCase):

    def test_default_values(self):
        km = killmail.Killmail()
        attrs = ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
            'corp_id', 'corp', 'alliance_id', 'alliance', 'verified',
            'url', 'value', 'timestamp', 'system', 'constellation',
            'region')
        for attr in attrs:
            self.assertTrue(getattr(km, attr) is None)

    def test_hidden_data(self):
        km = killmail.Killmail()
        old_dir = dir(km)
        km.foo = 'bar'
        new_dir = dir(km)
        self.assertEqual(old_dir, new_dir)
        self.assertTrue('foo' in km._data)
        self.assertEqual(km.foo, 'bar')

    def test_keyword_arguments(self):
        km = killmail.Killmail(kill_id=123456)


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
        self.assertTrue(km.requests_session is not None)

    def test_provided_session(self):
        session = object()
        km = self.SessionMixed(requests_session=session)
        self.assertTrue(km.requests_session is session)


class TestZkillmail(TestCase):
    pass


class TestCRESTmail(TestCase):
    pass




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
    pass

class TestLocationMixin(TestCase):
    pass


class TestRequestsMixin(TestCase):
    pass


class TestZkillmail(TestCase):
    pass


class TestCRESTmail(TestCase):
    pass




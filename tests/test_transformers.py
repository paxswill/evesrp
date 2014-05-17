from unittest import TestCase
from evesrp.transformers import ShipTransformer, PilotTransformer
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestShipTransformer(TestCase):

    def setUp(self):
        self.transformer = ShipTransformer('', '{name}/{id_}/{division}')

    def test_all_ship_tokens(self):
        self.assertEqual(self.transformer('foo', 'bar', 'baz'), 'bar/foo/baz')

    def test_ship_name_token(self):
        self.assertEqual(self.transformer(ship_name='foo'), 'foo//')

    def test_ship_id_token(self):
        self.assertEqual(self.transformer(ship_id='bar'), '/bar/')

    def test_ship_division_token(self):
        self.assertEqual(self.transformer(division='baz'), '//baz')


class TestPilotTransformer(TestCase):

    def setUp(self):
        self.pilot = MagicMock()
        self.pilot.name = 'foo'
        self.pilot.id = 'bar'


    def test_all_pilot_tokens(self):
        transformer = PilotTransformer('', '{name}/{id_}/{division}')
        self.assertEqual(transformer(self.pilot, 'baz'), 'foo/bar/baz')

    def test_pilot_name_token(self):
        transformer = PilotTransformer('', '{name}/{division}')
        self.assertEqual(transformer(self.pilot, 'baz'), 'foo/baz')

    def test_pilot_id_token(self):
        transformer = PilotTransformer('', '{id_}/{division}')
        self.assertEqual(transformer(self.pilot, 'baz'), 'bar/baz')

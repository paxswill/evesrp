from unittest import TestCase
from evesrp.transformers import Transformer
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestTransformer(TestCase):

    def test_equality(self):
        t1 = Transformer('Foo', 'Bar')
        t2 = Transformer('Foo', 'Bar')
        t3 = Transformer('Bar', 'Foo')
        self.assertEqual(t1, t2)
        self.assertNotEqual(t1, t3)
        self.assertNotEqual(t2, t3)


class TestTransformer(TestCase):

    def setUp(self):
        self.transformer = Transformer('', 'foo/{}')

    def test_transform(self):
        self.assertEqual(self.transformer('bar'), 'foo/bar')

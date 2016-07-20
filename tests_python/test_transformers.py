from evesrp.transformers import Transformer


class TestTransformer(object):

    def test_equality(self):
        t1 = Transformer('Foo', 'Bar')
        t2 = Transformer('Foo', 'Bar')
        t3 = Transformer('Bar', 'Foo')
        assert t1 == t2
        assert t1 != t3
        assert t2 != t3

    def test_transform(self):
        transformer = Transformer('', 'foo/{}')
        assert transformer('bar') == 'foo/bar'

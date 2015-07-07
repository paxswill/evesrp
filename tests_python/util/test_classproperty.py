from unittest import TestCase
from evesrp.util.classproperty import classproperty


class TestClassProperty(TestCase):

    def setUp(self):
        class Foo(object):
            @classproperty
            def bar(cls):
                return 'Baz'
        self.Foo = Foo

    def test_class_prop(self):
        self.assertEqual(self.Foo.bar, 'Baz')

    def test_class_instance(self):
        foo = self.Foo()
        self.assertEqual(foo.bar, 'Baz')

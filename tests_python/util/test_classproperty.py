import pytest
from evesrp.util.classproperty import classproperty


class TestClassProperty(object):

    @pytest.fixture(autouse=True)
    def property_class(self):
        class Foo(object):
            @classproperty
            def bar(cls):
                return 'Baz'
        self.Foo = Foo

    def test_class_prop(self):
        assert self.Foo.bar == 'Baz'

    def test_class_instance(self):
        foo = self.Foo()
        assert foo.bar == 'Baz'

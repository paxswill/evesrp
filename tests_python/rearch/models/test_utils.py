from collections import namedtuple
import datetime as dt
try:
    from unittest import mock
except ImportError:
    import mock

import pytest
from evesrp.util import utc
from evesrp.new_models import util
from evesrp.new_models import authorization as authz


def test_id_equality_eq():
    user = authz.User("User 1", 1)
    group = authz.Group("Group 1", 1)
    assert user == group


def test_id_equality_hash():
    user = authz.User("User 1", 1)
    group = authz.Group("Group 1", 1)
    assert hash(user) != hash(group)


def test_get_item_attribute():

    class TestItemAttribute(util.GetItemAttribute):
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    obj1 = TestItemAttribute(foo_=mock.sentinel.foo)
    assert obj1.foo_ == obj1['foo'] == obj1['foo_'] == mock.sentinel.foo


@pytest.mark.parametrize('kwargs', [
    # This is a bit of a weird way to get an object with an id_ attribute that
    # I've set, all in succint single line
    {'testing': namedtuple('Testing', 'id_')(7)},
    {'testing_id': 7},
])
def test_id_kwargs(kwargs):
    assert util.id_from_kwargs('testing', kwargs) == 7


@pytest.mark.parametrize('timestamp', [
    dt.datetime(2016, 12, 10, tzinfo=utc),
    '2016-12-10'
])
def test_parse_timestamp(timestamp):
    parsed_timestamp = util.parse_timestamp(timestamp)
    # Need to specify a timezone as iso8601 defaults to UTC
    assert parsed_timestamp == dt.datetime(2016, 12, 10, tzinfo=utc)


@pytest.mark.parametrize('field_type', (
    None,
    util.FieldType.integer,
    util.FieldType.app_id,
    util.FieldType.datetime,
    util.FieldType.decimal,
    'foo'
))
def test_field_set(field_type):
    test_fields = {
        'int_foo': util.FieldType.integer,
        'int_bar': util.FieldType.integer,
        'datetime_foo': util.FieldType.datetime,
        'datetime_bar': util.FieldType.datetime,
        'app_foo': util.FieldType.app_id,
        'app_bar': util.FieldType.app_id,
    }
    field_set = util._FieldTypeSet(test_fields)
    if field_type is None:
        assert set(test_fields.keys()) == field_set
    elif field_type == util.FieldType.integer:
        assert {'app_foo', 'app_bar', 'int_foo', 'int_bar'} == \
            field_set[field_type]
    elif field_type == util.FieldType.app_id:
        assert {'app_foo', 'app_bar'} == field_set[field_type]
    elif field_type == util.FieldType.datetime:
        assert {'datetime_foo', 'datetime_bar'} == field_set[field_type]
    elif field_type == util.FieldType.decimal:
        assert set() == field_set[field_type]
    elif field_type == 'foo':
        with pytest.raises(ValueError):
            assert field_set[field_type]


def test_fields_access(monkeypatch):
    FieldSetMock = mock.Mock()
    FieldSetMock.return_value = mock.sentinel.field_set
    monkeypatch.setattr(util, '_FieldTypeSet', FieldSetMock)

    class TestFieldsAccess(util.FieldsAccess):
        field_types = mock.sentinel.fields

    assert TestFieldsAccess.fields == mock.sentinel.field_set
    FieldSetMock.assert_called_once_with(mock.sentinel.fields)

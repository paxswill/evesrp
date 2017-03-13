from collections import namedtuple
import datetime as dt
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

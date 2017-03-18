import datetime as dt
from decimal import Decimal
try:
    from unittest import mock
except ImportError:
    import mock

import pytest
import evesrp
from evesrp import new_models as models
from evesrp import search_filter as sfilter


@pytest.mark.parametrize('initial_values', (None, {'division_id': {0, }}))
@pytest.mark.parametrize('additional_kwargs', ({}, {'division_id': {1, }}))
def test_filter_init(initial_values, additional_kwargs):
    test_filter = sfilter.Filter(initial_values, **additional_kwargs)
    if initial_values is None and len(additional_kwargs) == 0:
        assert len(test_filter._filters) == 0
    elif initial_values is not None and len(additional_kwargs) == 0:
        assert len(test_filter._filters) == 1
        assert test_filter._filters['division_id'] == {0, }
    elif initial_values is None and len(additional_kwargs) == 1:
        assert len(test_filter._filters) == 1
        assert test_filter._filters['division_id'] == {1, }
    elif initial_values is not None and len(additional_kwargs) == 1:
        assert len(test_filter._filters) == 1
        assert test_filter._filters['division_id'] == {0, 1}


def test_filter_length():
    filter_ = sfilter.Filter()
    assert len(filter_) == 0
    filter_._filters['killmail_id'].add(1)
    assert len(filter_) == 1
    filter_._filters['killmail_id'].add(2)
    assert len(filter_) == 1
    filter_._filters['request_id'].add(3)
    assert len(filter_) == 2


def test_filter_iter():
    filter_ = sfilter.Filter()
    filter_._filters = {
        'request_id': {1, 2, 3},
        'killmail_id': {4, 5},
    }
    keys = set(filter_._filters.keys())
    for key, value in filter_:
        keys.remove(key)
        assert frozenset(filter_._filters[key]) == value
    assert len(keys) == 0


def test_filter_contains():
    test_filter = sfilter.Filter()
    assert 'killmail_id' not in test_filter
    test_filter._filters['killmail_id'].add(1)
    assert 'killmail_id' in test_filter


def test_filter_getitem():
    f = sfilter.Filter()
    assert f['division_id'] == set()
    with pytest.raises(KeyError):
        f['character']
    assert isinstance(f['division_id'], frozenset)


def test_filter_equals():
    filter1 = sfilter.Filter()
    filter2 = sfilter.Filter()
    assert filter1 == filter2
    filter1._filters['division_id'].add(1)
    filter2._filters['division_id'].add(1)
    assert filter1 == filter2
    filter1._filters['division_id'].add(2)
    assert filter1 != filter2


def test_filter_repr():
    test_filter = sfilter.Filter()
    assert repr(test_filter) == "Filter({})"
    test_filter._filters['division_id'].add(2)
    assert repr(test_filter) == "Filter({'division_id': {2}})"


def test_filter_merge():
    starting_filter = sfilter.Filter()
    starting_filter._filters['division_id'].add(1)
    other_filter = sfilter.Filter()
    other_filter._filters['division_id'].add(2)
    other_filter._filters['character_id'].add(10)
    starting_filter.merge(other_filter)
    assert starting_filter._filters == {
        'division_id': {1, 2},
        'character_id': {10, },
    }


class TestMatches(object):

    @pytest.fixture
    def srp_request(self):
        return mock.Mock(killmail_id=0, division_id=10)

    @pytest.fixture
    def killmail(self):
        return mock.Mock(id_=0, type_id=100)

    @pytest.mark.parametrize('killmail',(mock.Mock(id_=1), ))
    def test_mismatched_killmail(self, srp_request, killmail):
        test_filter = sfilter.Filter()
        with pytest.raises(ValueError):
            test_filter.matches(srp_request, killmail)

    def test_matches_killmail(self, srp_request, killmail):
        test_filter = sfilter.Filter(type_id={100, })
        assert test_filter.matches(srp_request, killmail)

    def test_matches_request(self, srp_request):
        test_filter = sfilter.Filter(division_id={10, })
        assert test_filter.matches(srp_request)

    def test_not_matches(self, srp_request):
        test_filter = sfilter.Filter(division_id={20, })
        assert not test_filter.matches(srp_request)



integer_values = (0, 1, 2)


period_values = (
    u'2014-11-20',
    (dt.datetime(2014, 12, 24), dt.datetime(2015, 12, 24)),
)


decimal_values = (
    u'1000000',
    Decimal('1000000'),
    1000000,
)


status_values = list((s.name for s in models.ActionType.statuses))
status_values.append(models.ActionType.approved)


url_values = (
    'http://example.com',
    'http://example.com/foo/bar/baz',
)


def convert_value(field_type, field_value):
    if field_type == models.FieldType.decimal:
        return Decimal(field_value)
    elif field_type == models.FieldType.datetime:
        if not isinstance(field_value, tuple):
            return evesrp.util.parse_datetime(field_value)
        else:
            return field_value
    elif field_type == models.FieldType.status:
        if field_value in models.ActionType:
            return field_value
        else:
            return models.ActionType[field_value]
    else:
        return field_value


class TestPredicate(object):


    @pytest.mark.parametrize('field_name,field_type',
                             sfilter.Filter._field_types.items())
    def test_add_predicate(self, field_name, field_type):
        if field_type == models.FieldType.decimal:
            values = decimal_values
        elif field_type == models.FieldType.datetime:
            values = period_values
        elif field_type == models.FieldType.status:
            values = status_values
        elif field_type in (models.FieldType.string,
                            models.FieldType.text,
                            models.FieldType.url):
            values = url_values
        elif field_type in (models.FieldType.integer,
                            models.FieldType.app_id,
                            models.FieldType.ccp_id):
            values = integer_values
        added_values = set()
        test_filter = sfilter.Filter()
        for value in values:
            added_values.add(convert_value(field_type, value))
            test_filter.add(field_name, value)
            assert test_filter._filters[field_name] == added_values

    @pytest.mark.parametrize('valid_field', (True, False),
                             ids=('valid_field', 'invalid_field'))
    def test_remove_empty(self, valid_field):
        test_filter = sfilter.Filter()
        if valid_field:
            # Testing that it doesn't raise
            test_filter.remove('division_id', 0)
        else:
            with pytest.raises(sfilter.InvalidFilterKeyError):
                test_filter.remove('foo', 0)

    def test_remove_last(self):
        test_filter = sfilter.Filter(division_id=(0, ))
        assert len(test_filter) == 1
        test_filter.remove('division_id', 0)
        assert len(test_filter) == 0

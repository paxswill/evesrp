import datetime as dt
from decimal import Decimal
import itertools
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
import six
import evesrp
from evesrp import new_models as models
from evesrp import search_filter as sfilter


@pytest.fixture(params=(True, False))
def immutable(request):
    return request.param


def test_filter_init(immutable):
    default_filter = sfilter.Filter()
    assert default_filter._immutable
    assert default_filter._filters == {}
    immutability_filter = sfilter.Filter(filter_immutable=immutable)
    assert immutability_filter._immutable == immutable
    source_filter = mock.Mock()
    source_filter._filters = mock.sentinel.sourced_filters
    with mock.patch('copy.deepcopy', autospec=True) as mock_deepcopy:
        mock_deepcopy.return_value = mock.sentinel.copied_filters
        sourced_filter = sfilter.Filter(filter_source=source_filter)
        mock_deepcopy.assert_called_once_with(mock.sentinel.sourced_filters)
        assert sourced_filter._filters == mock.sentinel.copied_filters


def test_filter_length():
    filter_ = sfilter.Filter()
    assert len(filter_) == 0
    filter_._filters['foo'].add(1)
    assert len(filter_) == 1
    filter_._filters['foo'].add(2)
    assert len(filter_) == 1
    filter_._filters['bar'].add(3)
    assert len(filter_) == 2
    del filter_._filters['foo']


def test_filter_iter():
    filter_ = sfilter.Filter()
    filter_._filters = {
        'foo': {1, 2, 3},
        'bar': {4, 5},
    }
    keys = set(filter_._filters.keys())
    for key, value in filter_:
        keys.remove(key)
        assert frozenset(filter_._filters[key]) == value
    assert len(keys) == 0


def test_filter_contains():
    test_filter = sfilter.Filter()
    assert len(test_filter) == 0
    test_filter = test_filter.add(division=1)
    assert len(test_filter) == 1
    # Adding another item to an existing field does not change the length
    test_filter = test_filter.add(division=2)
    assert len(test_filter) == 1


def test_filter_getitem():
    f = sfilter.Filter()
    assert f['division'] == set()
    with pytest.raises(KeyError):
        f['character']
    assert isinstance(f['division'], frozenset)
    f = f.add(division=5)
    assert f['division'] == {5, }


def test_filter_equals():
    assert sfilter.Filter() == sfilter.Filter()
    assert sfilter.Filter().add(division=2) == sfilter.Filter().add(division=2)
    assert sfilter.Filter().add(division=2) != sfilter.Filter().add(division=0)


def test_filter_repr():
    f = sfilter.Filter()
    assert repr(f) == "Filter({})"
    f = f.add(division=2)
    assert repr(f) == "Filter({'division': {2}})"


def test_filter_merge():
    starting_filter = sfilter.Filter().add(division=1)
    assert starting_filter['division'] == {1, }
    other_filter = sfilter.Filter().add(division=2).add(pilot=u'Paxswill')
    assert other_filter['division'] == {2, }
    assert other_filter['pilot'] == {u'Paxswill', }
    merged_filter = starting_filter.merge(other_filter)
    expected_filter = sfilter.Filter().\
        add(pilot=u'Paxswill').\
        add(division=1).\
        add(division=2)
    assert merged_filter == expected_filter


string_or_id_values = {
    'type': (u'Erebus', u'Ragnarok', 671, u'Megathron',),
    # "Numbers" is my favorite test case.
    # https://github.com/bravecollective/core/issues/264
    'pilot': (u'17007870', 91447153, u'Paxswill', u'DurrHurrDurr',),
    'region': (10000014, u'Catch', u'The Forge',),
    'constellation': (u'T-HHHT', u'Inolari', 20000020,),
    'system': (30000142, u'Poitot', u'Jita'),
}


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


all_values = dict(
    string_or_id_values,
    kill_timestamp=period_values,
    submit_timestamp=period_values,
    payout=decimal_values,
    base_payout=decimal_values,
    division=(1, 2, 3),
    user=(1, 2, 3),
    status=status_values,
    details=(u'a details search', u'another search'),
)


@pytest.fixture
def convert_value(attribute):
    if attribute.endswith('payout'):
        return lambda v: Decimal(v)
    elif attribute.endswith('_timestamp'):
        def _convert_datatime(value):
            if not isinstance(value, tuple):
                return evesrp.util.parse_datetime(value)
            else:
                return value
        return _convert_datatime
    elif attribute == 'status':
        def _convert_actiontype(value):
            if value in models.ActionType:
                return value
            else:
                return models.ActionType[value]
        return _convert_actiontype
    else:
        return lambda v: v


class TestAddPredicate(object):

    @pytest.mark.parametrize(
        'attribute,value',
        ((attrib, value) for attrib, values in six.iteritems(all_values)
         for value in values)
    )
    def test_single_predicates(self, attribute, value, immutable,
                               convert_value):
        start_filter = sfilter.Filter(filter_immutable=immutable)
        kwargs = {attribute: value}
        test_filter = start_filter.add(**kwargs)
        assert test_filter._filters == {attribute: {convert_value(value)}}
        if immutable:
            assert id(start_filter) != id(test_filter)
            assert start_filter._filters == {}
        else:
            assert id(start_filter) == id(test_filter)

    @pytest.mark.parametrize(
        'attribute,values',
        ((attrib, value) for attrib, values in six.iteritems(all_values)
         for value in itertools.combinations(values, 2))
    )
    def test_multiple_predicates(self, attribute, values, immutable,
                                 convert_value):
        first, second = values
        start_filter = sfilter.Filter(filter_immutable=immutable)
        kwargs = {attribute: first}
        mid_filter = start_filter.add(**kwargs)
        assert mid_filter._filters == {attribute: {convert_value(first)}}
        if immutable:
            assert id(start_filter) != id(mid_filter)
            assert start_filter._filters == {}
        else:
            assert id(start_filter) == id(mid_filter)
        end_filter = mid_filter.add(**{attribute: second})
        assert end_filter._filters == {attribute: {convert_value(first),
                                                   convert_value(second)}}
        if immutable:
            assert id(mid_filter) != id(end_filter)
            assert mid_filter._filters == {attribute: {convert_value(first)}}
        else:
            assert id(start_filter) == id(mid_filter)
            assert id(mid_filter) == id(end_filter)

    @pytest.mark.parametrize(
        'attribute, value',
        ((key, 3.14159) for key in six.iterkeys(string_or_id_values))
    )
    def test_invalid_string_predicates(self, attribute, value):
        filter_ = sfilter.Filter()
        kwargs = {attribute: value}
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            filter_.add(**kwargs)
        assert excinfo.value.key == attribute
        assert excinfo.value.value == value

    @pytest.mark.parametrize('attribute', (
        'submit_timestamp',
        'kill_timestamp',
    ))
    @pytest.mark.parametrize('value', ('foo', dt.datetime(2016, 12, 24)))
    def test_invalid_period_predicates(self, attribute, value):
        kwargs = {attribute: value}
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            sfilter.Filter().add(**kwargs)
        assert excinfo.value.key == attribute
        assert excinfo.value.value == value

    @pytest.mark.parametrize('attribute', ('payout', 'base_payout'))
    def test_invalid_decimal_predicates(self, attribute):
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            sfilter.Filter().add(**{attribute: 'foo'})
        assert excinfo.value.key == attribute
        assert excinfo.value.value == 'foo'

    @pytest.mark.parametrize('value', ('foo', 'comment'))
    def test_invalid_status_predicates(self, value):
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            sfilter.Filter().add(status=value)
        assert excinfo.value.key == 'status'
        assert excinfo.value.value == value

    @pytest.mark.parametrize('attribute', ('division', 'user'))
    def test_invalid_int_predicates(self, attribute):
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            sfilter.Filter().add(**{attribute: 'foo'})
        assert excinfo.value.key == attribute
        assert excinfo.value.value == 'foo'

    def test_invalid_attribute(self):
        with pytest.raises(sfilter.InvalidFilterKeyError) as excinfo:
            sfilter.Filter().add(foo='bar')
        assert excinfo.value.key == 'foo'


class TestRemovePredicates(object):

    @pytest.mark.parametrize(
        'attribute,value',
        ((att, value) for att, values in six.iteritems(all_values)
         for value in values)
    )
    def test_single_predicates(self, attribute, value, immutable,
                               convert_value):
        start_filter = sfilter.Filter(filter_immutable=immutable)
        start_filter._filters[attribute].add(convert_value(value))
        kwargs = {attribute: value}
        test_filter = start_filter.remove(**kwargs)
        assert test_filter._filters == {}
        if immutable:
            assert id(start_filter) != id(test_filter)
            assert start_filter._filters == {
                attribute: {
                    convert_value(value),
                },
            }
        else:
            assert id(start_filter) == id(test_filter)

    def test_invalid_attribute(self):
        with pytest.raises(sfilter.InvalidFilterKeyError) as excinfo:
            sfilter.Filter().add(foo='bar')
        assert excinfo.value.key == 'foo'

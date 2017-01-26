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
    assert default_filter._immutable == True
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


all_values = dict(string_or_id_values,
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

    @pytest.mark.parametrize('attribute,value',
        ((attrib, value) for attrib, values in six.iteritems(all_values) \
            for value in values)
    )
    def test_single_predicates(self, attribute, value, immutable,
                               convert_value):
        start_filter = sfilter.Filter(filter_immutable=immutable)
        kwargs = {attribute: value}
        test_filter = start_filter.add(**kwargs)
        assert test_filter._filters == {attribute: {convert_value(value),}}
        if immutable:
            assert id(start_filter) != id(test_filter)
            assert start_filter._filters == {}
        else:
            assert id(start_filter) == id(test_filter)

    @pytest.mark.parametrize('attribute,values',
        ((attrib, value) for attrib, values in six.iteritems(all_values) \
            for value in itertools.combinations(values, 2))
    )
    def test_multiple_predicates(self, attribute, values, immutable,
                                 convert_value):
        first, second = values
        start_filter = sfilter.Filter(filter_immutable=immutable)
        kwargs = {attribute: first}
        mid_filter = start_filter.add(**kwargs)
        assert mid_filter._filters == {attribute: {convert_value(first),}}
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
            assert mid_filter._filters == {attribute: {convert_value(first),}}
        else:
            assert id(start_filter) == id(mid_filter)
            assert id(mid_filter) == id(end_filter)

    @pytest.mark.parametrize('attribute, value',
        ((key, 3.14159) for key in six.iterkeys(string_or_id_values))
    )
    def test_invalid_string_predicates(self, attribute, value):
        filter_ = sfilter.Filter()
        kwargs = {attribute: value}
        with pytest.raises(sfilter.InvalidFilterValueError) as excinfo:
            filter_.add(**kwargs)
        assert excinfo.value.key == attribute
        assert excinfo.value.value == value

    @pytest.mark.parametrize('attribute', ('submit_timestamp', 'kill_timestamp'))
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

    @pytest.mark.parametrize('attribute,value',
        ((attrib, value) for attrib, values in six.iteritems(all_values) \
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
            assert start_filter._filters == {attribute: {convert_value(value),}}
        else:
            assert id(start_filter) == id(test_filter)

    def test_invalid_attribute(self):
        with pytest.raises(sfilter.InvalidFilterKeyError) as excinfo:
            sfilter.Filter().add(foo='bar')
        assert excinfo.value.key == 'foo'


def test_personal_filter():
    user = mock.Mock(id_=2)
    personal_filter = sfilter.Filter.personal_filter(user)
    target_filters = {
        'user': frozenset((2,)),
    }


@pytest.mark.parametrize('division_ids', (
    (1,),
    (2, 3),
))
@pytest.mark.parametrize('filter_type', ('reviewer', 'payer'))
def test_reviewer_filter(division_ids, filter_type):
    divisions = (mock.Mock(id_=d_id) for d_id in division_ids)
    filter_class_method = getattr(sfilter.Filter, filter_type + '_filter')
    filter_ = filter_class_method(divisions)
    if filter_type == 'reviewer':
        status_filter = frozenset((models.ActionType.evaluating,
                                   models.ActionType.incomplete,
                                   models.ActionType.approved))
    elif filter_type == 'payer':
        status_filter = frozenset((models.ActionType.approved,))
    target_filters = {
        'status': status_filter,
        'division': frozenset(division_ids),
    }
    assert dict(filter_) == target_filters

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


def test_search_init():
    test_filter = sfilter.Search()
    assert len(test_filter._filters) == 0
    assert len(test_filter._sorts) == 0


def test_search_contains():
    test_filter = sfilter.Search()
    assert 'killmail_id' not in test_filter
    test_filter.add_filter('killmail_id', 1)
    assert 'killmail_id' in test_filter


def test_search_getitem():
    search = sfilter.Search()
    # Empty filter
    assert isinstance(search['division_id'], set)
    # Fill in the filter a little
    search.add_filter('division_id', 1)
    assert search['division_id'] == {(1, sfilter.PredicateType.equal), }
    search.add_filter('division_id', 2)
    assert search['division_id'] == {
        (1, sfilter.PredicateType.equal),
        (2, sfilter.PredicateType.equal),
    }
    search.add_filter('division_id', 3,
                      predicate=sfilter.PredicateType.not_equal)
    assert search['division_id'] == {
        (1, sfilter.PredicateType.equal),
        (2, sfilter.PredicateType.equal),
        (3, sfilter.PredicateType.not_equal),
    }


def test_search_equals():
    filter1 = sfilter.Search()
    filter2 = sfilter.Search()
    # Empty filters
    assert filter1 == filter2
    filter1.add_filter('division_id', 1)
    filter2.add_filter('division_id', 1)
    assert filter1 == filter2
    filter1.add_filter('division_id', 2)
    assert filter1 != filter2
    filter1.remove_filter('division_id', 2)
    # Adding and removing filters doesn't change the identity
    assert filter1 == filter2
    # Adding and removing sorts
    filter1.add_sort('killmail_id')
    filter2.add_sort('killmail_id')
    assert filter1 == filter2
    filter1.add_sort('type_name')
    assert filter1 != filter2


def test_search_repr():
    search = sfilter.Search()
    assert repr(search) == "Search({})"
    search.add_filter('division_id', 2)
    assert repr(search) == "Search({'division_id': {2}})"


class TestSearchFiltersIterables(object):

    def assert_filters_iterable(self, iterable_function):
        search = sfilter.Search()
        search.add_filter('request_id', 1, 2, 3)
        assert list(iterable_function(search)) == [
            (
                'request_id',
                {
                    (1, sfilter.PredicateType.equal),
                    (2, sfilter.PredicateType.equal),
                    (3, sfilter.PredicateType.equal),
                },
            ),
        ]
        search.add_filter('killmail_id', 4, 5)
        expected = [
            (
                'killmail_id',
                {
                    (4, sfilter.PredicateType.equal),
                    (5, sfilter.PredicateType.equal),
                },
            ),
            (
                'request_id',
                {
                    (1, sfilter.PredicateType.equal),
                    (2, sfilter.PredicateType.equal),
                    (3, sfilter.PredicateType.equal),
                },
            ),
        ]
        actual = list(iterable_function(search))
        # Sort the actual list to remove inconsistencies in ordering
        # (which isn't specified).
        actual.sort(key=lambda k: k[0])
        assert actual == expected

    def test_search_iter(self):

        def magic_iter(search):
            return iter(search)
        self.assert_filters_iterable(magic_iter)

    def test_search_fields(self):

        def filters_iter(search):
            return search.filters
        self.assert_filters_iterable(filters_iter)

    def test_simplified_fields_text(self):
        search = sfilter.Search()
        search.add_filter('details', 'Foo', 'Bar')
        assert list(search.simplified_filters) == [
            (
                'details',
                {
                    ('Foo', None),
                    ('Bar', None),
                },
            ),
        ]

    def test_simplified_fields_exact(self):
        search = sfilter.Search()
        search.add_filter('request_id', 1, 2)
        assert list(search.simplified_filters) == [
            (
                'request_id',
                {
                    (1, sfilter.PredicateType.equal),
                    (2, sfilter.PredicateType.equal),
                },
            ),
        ]
        search.add_filter('request_id', 2,
                          predicate=sfilter.PredicateType.not_equal)
        expected_simplified = [
            (
                'request_id',
                {
                    (1, sfilter.PredicateType.equal),
                    (2, sfilter.PredicateType.any),
                },
            ),
        ]
        assert list(search.simplified_filters) == expected_simplified
        # This assert is to make sure that more than 2 predicates are
        # reduced properly
        search.add_filter('request_id', 2,
                          predicate=sfilter.PredicateType.not_equal)
        assert list(search.simplified_filters) == expected_simplified

    def test_simplified_field_range(self):
        search = sfilter.Search()
        search.add_filter('payout', 100, 200,
                          predicate=sfilter.PredicateType.greater_equal)
        assert list(search.simplified_filters) == [
            (
                'payout',
                {
                    (Decimal(100), sfilter.PredicateType.greater_equal),
                    (Decimal(200), sfilter.PredicateType.greater_equal),
                },
            ),
        ]
        search.add_filter('payout', 200,
                          predicate=sfilter.PredicateType.greater)
        expected_simplified = [
            (
                'payout',
                {
                    (Decimal(100), sfilter.PredicateType.greater_equal),
                    (Decimal(200), sfilter.PredicateType.greater),
                },
            ),
        ]
        assert list(search.simplified_filters) == expected_simplified
        # Again, testing the more than two case for reduce
        search.add_filter('payout', 200,
                          predicate=sfilter.PredicateType.greater_equal)
        assert list(search.simplified_filters) == expected_simplified
        # And finally, checking that filters are set to PredicateType.none
        # correctly.
        search.add_filter('payout', 100,
                          predicate=sfilter.PredicateType.less)
        assert list(search.simplified_filters) == [
            (
                'payout',
                {
                    (Decimal(100), sfilter.PredicateType.none),
                    (Decimal(200), sfilter.PredicateType.greater),
                },
            ),
        ]


class TestSearchSort(object):

    def test_add_new_sort(self):
        search = sfilter.Search()
        assert len(list(search.sorts)) == 0
        search.add_sort('type_name', sfilter.SortDirection.ascending)
        assert len(list(search.sorts)) == 1

    def test_add_bad_sort(self):
        search = sfilter.Search()
        with pytest.raises(ValueError):
            search.add_sort('type_id')

    def test_add_bad_direction(self):
        search = sfilter.Search()
        with pytest.raises(TypeError):
            search.add_sort('type_name', None)

    def test_add_existing_sort(self):
        search = sfilter.Search()
        search.set_default_sort()
        search.add_sort('request_timestamp', sfilter.SortDirection.descending)
        assert list(search.sorts) == [
            ('status', sfilter.SortDirection.ascending),
            ('request_timestamp', sfilter.SortDirection.descending),
        ]

    def test_remove_sort(self):
        search = sfilter.Search()
        search.set_default_sort()
        search.remove_sort('status')
        assert list(search.sorts) == [
            ('request_timestamp', sfilter.SortDirection.ascending),
        ]

    def test_remove_nonexistant_sort(self):
        search = sfilter.Search()
        search.set_default_sort()
        with pytest.raises(ValueError):
            search.remove_sort('submit_timestamp')

    def test_set_default(self):
        search = sfilter.Search()
        assert len(list(search.sorts)) == 0
        search.set_default_sort()
        assert list(search.sorts) == [
            ('status', sfilter.SortDirection.ascending),
            ('request_timestamp', sfilter.SortDirection.ascending),
        ]

    def test_clear_sorts(self):
        search = sfilter.Search()
        search.set_default_sort()
        assert len(list(search.sorts)) == 2
        search.clear_sorts()
        assert len(list(search.sorts)) == 0


class TestSearchFilter(object):

    def test_invalid_field(self):
        search = sfilter.Search()
        with pytest.raises(sfilter.InvalidFilterKeyError) as exc:
            search.add_filter('not_a_field', None)
        assert exc.value.key == 'not_a_field'

    @pytest.mark.parametrize(
        'field_name,predicate',
        (
            ('division_id', sfilter.PredicateType.less),
            ('character_id', sfilter.PredicateType.less),
        ),
    )
    def test_invalid_predicate(self, field_name, predicate):
        search = sfilter.Search()
        with pytest.raises(sfilter.InvalidFilterPredicateError) as exc:
            search.add_filter(field_name, None, predicate=predicate)
        assert exc.value.key == field_name
        assert exc.value.predicate == predicate

    @pytest.mark.parametrize(
        'field_name,predicate',
        (
            ('details', None),
            # Predicates are ignored for text field
            ('details', sfilter.PredicateType.equal),
            ('division_id', None),
        ),
    )
    def test_predicate_skipped(self, field_name, predicate):
        search = sfilter.Search()
        # It's still going to raise, but for the value we're using (None)
        with pytest.raises(sfilter.InvalidFilterValueError) as exc:
            search.add_filter(field_name, None, predicate=predicate)
        assert exc.value.key == field_name
        assert exc.value.value == None

    @pytest.mark.parametrize(
        'field_name,dirty,clean',
        (
            # None is being used to signal that an exception is raised
            ('killmail_timestamp', '2016-01-31', None),
            ('killmail_timestamp', dt.datetime(2016, 1, 31),
             dt.datetime(2016, 1, 31)),
            ('payout', '100', Decimal(100)),
            ('payout', 100, Decimal(100)),
            ('payout', '0.1', Decimal('0.1')),
            ('payout', Decimal('100.01'), Decimal('100.01')),
            ('status', models.ActionType.approved, models.ActionType.approved),
            ('status', 'approved', models.ActionType.approved),
            ('status', 'not_a_status', None),
            ('division_id', 1, 1),
            ('division_id', 'not_an_int', None),
            ('url', 'http://example.com', 'http://example.com'),
            ('url', 1, None),
        ),
    )
    def test_sanitize(self, field_name, dirty, clean):
        search = sfilter.Search()
        if clean is None:
            with pytest.raises(sfilter.InvalidFilterValueError) as exc:
                search.add_filter(field_name, dirty)
            assert exc.value.key == field_name
            assert exc.value.value == dirty
        else:
            search.add_filter(field_name, dirty)
            assert search[field_name] == {
                (clean, sfilter.PredicateType.equal),
            }

    def test_add_multiple(self):
        search = sfilter.Search()
        assert len(search['division_id']) == 0
        search.add_filter('division_id', 1, 2, 3, 4)
        assert len(search['division_id']) == 4
        # Duplicate filters are ignored
        search.add_filter('division_id', 2, 3, 3, 5)
        assert len(search['division_id']) == 5

    def test_remove(self):
        search = sfilter.Search()
        assert len(list(search)) == 0
        search.add_filter('division_id', 1, 2, 3, 4, 5)
        search.add_filter('division_id', 1, 3, 5,
                          predicate=sfilter.PredicateType.not_equal)
        assert len(search['division_id']) == 8
        assert len(list(search)) == 1
        search.remove_filter('division_id', 1,
                             predicate=sfilter.PredicateType.not_equal)
        assert len(search['division_id']) == 7
        search.remove_filter('division_id', 5)
        assert len(search['division_id']) == 5
        search.remove_filter('division_id', 1, 2, 3, 4)
        assert len(search['division_id']) == 0
        assert len(list(search)) == 0


class TestMerge(object):

    def assert_preconditions(self, search):
        assert len(list(search)) == 1
        assert len(search['division_id']) == 2

    @pytest.fixture
    def search(self):
        initial_search = sfilter.Search()
        initial_search.add_filter('division_id', 1, 2)
        return initial_search

    def test_none(self, search):
        self.assert_preconditions(search)
        search.merge(None)
        self.assert_preconditions(search)

    def test_empty(self, search):
        empty_search = sfilter.Search()
        search.merge(empty_search)
        self.assert_preconditions(search)

    def test_self(self, search):
        self.assert_preconditions(search)
        search.merge(search)
        self.assert_preconditions(search)

    def test_filters(self, search):
        other_search = sfilter.Search()
        other_search.add_filter('character_id', 10)
        other_search.add_filter('division_id', 3)
        search.merge(other_search)
        assert len(list(search)) == 2
        assert len(search['division_id']) == 3

    def test_skip_sort(self, search):
        assert len(list(search.sorts)) == 0
        search.add_sort('character_name')
        assert len(list(search.sorts)) == 1
        other_search = sfilter.Search()
        other_search.add_sort('status')
        other_search.add_sort('request_timestamp')
        search.merge(other_search)
        assert len(list(search.sorts)) == 1

    def test_merge_sorts(self, search):
        assert len(list(search.sorts)) == 0
        other_search = sfilter.Search()
        other_search.add_sort('status')
        other_search.add_sort('request_timestamp')
        search.merge(other_search)
        assert len(list(search.sorts)) == 2


class TestMatches(object):

    @pytest.fixture
    def srp_request(self):
        return mock.Mock(killmail_id=0, division_id=10,
                         payout=Decimal(100), details='Some details',
                         timestamp=dt.datetime(2017, 7, 4))

    @pytest.fixture
    def killmail(self):
        return mock.Mock(id_=0, type_id=100, timestamp=dt.datetime(2016, 7, 4))

    @pytest.mark.parametrize('killmail',(mock.Mock(id_=1), ))
    def test_mismatched_killmail(self, srp_request, killmail):
        search = sfilter.Search()
        with pytest.raises(ValueError):
            search.matches(srp_request, killmail)

    @pytest.mark.parametrize(
        'field_name,values,predicate',
        (
            ('type_id', (100, ), sfilter.PredicateType.equal),
            ('type_id', (200, ), sfilter.PredicateType.not_equal),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 4), ),
                sfilter.PredicateType.equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 1, 1), ),
                sfilter.PredicateType.not_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 2), ),
                sfilter.PredicateType.greater,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2018, 7, 2), ),
                sfilter.PredicateType.less,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 4), ),
                sfilter.PredicateType.greater_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 5, 1), ),
                sfilter.PredicateType.greater_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 4), ),
                sfilter.PredicateType.less_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 8, 2), ),
                sfilter.PredicateType.less_equal,
            ),
        )
    )
    def test_matches_killmail_single(self, srp_request, killmail, field_name,
                                     values, predicate):
        search = sfilter.Search()
        search.add_filter(field_name, *values, predicate=predicate)
        assert search.matches(srp_request, killmail)

    @pytest.mark.parametrize(
        'field_name,values,predicate',
        (
            ('division_id', (10, ), sfilter.PredicateType.equal),
            ('division_id', (20, ), sfilter.PredicateType.not_equal),
            ('payout', (100, ), sfilter.PredicateType.equal),
            ('payout', (0, ), sfilter.PredicateType.not_equal),
            ('payout', (300, ), sfilter.PredicateType.less),
            ('payout', (100, ), sfilter.PredicateType.less_equal),
            ('payout', (400, ), sfilter.PredicateType.less_equal),
            ('payout', (50, ), sfilter.PredicateType.greater),
            ('payout', (100, ), sfilter.PredicateType.greater_equal),
            ('payout', (25, ), sfilter.PredicateType.greater_equal),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 4), ),
                sfilter.PredicateType.equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 1, 1), ),
                sfilter.PredicateType.not_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 2), ),
                sfilter.PredicateType.greater,
            ),
            (
                'request_timestamp',
                (dt.datetime(2018, 7, 2), ),
                sfilter.PredicateType.less,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 4), ),
                sfilter.PredicateType.greater_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 5, 1), ),
                sfilter.PredicateType.greater_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 4), ),
                sfilter.PredicateType.less_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 8, 2), ),
                sfilter.PredicateType.less_equal,
            ),
            ('details', ('Some', ), None),
            ('details', ('some', ), None),
            ('details', ('e d', ), None),
        )
    )
    def test_matches_request_single(self, srp_request, field_name, values,
                                    predicate):
        search = sfilter.Search()
        search.add_filter(field_name, *values, predicate=predicate)
        assert search.matches(srp_request)

    @pytest.mark.parametrize(
        'field_name,values,predicate',
        (
            ('type_id', (100, ), sfilter.PredicateType.not_equal),
            ('type_id', (200, ), sfilter.PredicateType.equal),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 4), ),
                sfilter.PredicateType.not_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 1, 1), ),
                sfilter.PredicateType.equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 7, 2), ),
                sfilter.PredicateType.less,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2018, 7, 2), ),
                sfilter.PredicateType.greater,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 5, 1), ),
                sfilter.PredicateType.less_equal,
            ),
            (
                'killmail_timestamp',
                (dt.datetime(2016, 8, 2), ),
                sfilter.PredicateType.greater_equal,
            ),
            ('division_id', (10, ), sfilter.PredicateType.not_equal),
            ('division_id', (20, ), sfilter.PredicateType.equal),
            ('payout', (100, ), sfilter.PredicateType.not_equal),
            ('payout', (0, ), sfilter.PredicateType.equal),
            ('payout', (300, ), sfilter.PredicateType.greater),
            ('payout', (400, ), sfilter.PredicateType.greater_equal),
            ('payout', (50, ), sfilter.PredicateType.less),
            ('payout', (25, ), sfilter.PredicateType.less_equal),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 4), ),
                sfilter.PredicateType.not_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 1, 1), ),
                sfilter.PredicateType.equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 7, 2), ),
                sfilter.PredicateType.less,
            ),
            (
                'request_timestamp',
                (dt.datetime(2018, 7, 2), ),
                sfilter.PredicateType.greater,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 5, 1), ),
                sfilter.PredicateType.less_equal,
            ),
            (
                'request_timestamp',
                (dt.datetime(2017, 8, 2), ),
                sfilter.PredicateType.greater_equal,
            ),
            ('details', ('Foo', ), None),
            ('details', ('foo', ), None),
        )
    )
    def test_not_matches_single(self, srp_request, killmail, field_name,
                                values, predicate):
        search = sfilter.Search()
        search.add_filter(field_name, *values, predicate=predicate)
        assert not search.matches(srp_request, killmail)

    def test_matches_multiple_exact(self, srp_request, killmail):
        search = sfilter.Search()
        search.add_filter('type_id', 100, 200)
        assert search.matches(srp_request, killmail)
        search.add_filter('type_id', 100,
                          predicate=sfilter.PredicateType.not_equal)
        assert search.matches(srp_request, killmail)

    def test_matches_multiple_range(self, srp_request, killmail):
        search = sfilter.Search()
        search.add_filter('payout', 50, 100,
                          predicate=sfilter.PredicateType.greater_equal)
        assert search.matches(srp_request, killmail)
        search.add_filter('payout', 50,
                          predicate=sfilter.PredicateType.not_equal)
        assert search.matches(srp_request, killmail)

    def test_matches_multiple_text(self, srp_request, killmail):
        search = sfilter.Search()
        search.add_filter('details', 'Some', 'DETAILS')
        assert search.matches(srp_request, killmail)
        search.add_filter('details', 'e d')
        assert search.matches(srp_request, killmail)

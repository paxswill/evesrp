import datetime as dt
import decimal
import itertools

import graphene
import graphene.types.datetime
from graphene.utils.str_converters import to_camel_case, to_snake_case
import pytest
import six

from evesrp import new_models as models
from evesrp import search_filter
from evesrp.graphql import types
import evesrp.graphql.types.request
import evesrp.graphql.types.decimal
import evesrp.graphql.types.connection


@pytest.fixture(params=(True, False), ids=('input', 'output'))
def is_input(request):
    return request.param


def test_sort_key():
    # Peek into the meta variable to get the stdlib Enum because that supports
    # iteration unlike graphene's halfway implementation.
    names = {e.name for e in types.SortKey._meta.enum}
    expected_names = set(models.Killmail.sorts)
    expected_names.update(models.Request.sorts)
    assert names == expected_names


class TestSearchTypes(object):

    def test_type_creation(self, is_input):
        if is_input:
            SearchType = types.InputRequestSearch
            assert issubclass(SearchType, graphene.InputObjectType)
        else:
            SearchType = types.RequestSearch
            assert issubclass(SearchType, graphene.ObjectType)
        search_fields = SearchType._meta.fields
        assert 'sorts' in search_fields
        all_fields = itertools.chain(
            six.iteritems(models.Killmail.field_types),
            six.iteritems(models.Request.field_types)
        )
        suffix_format = '{}__{}'
        # Make sure that all searchable fields are represented with the correct
        # names and with the correct types.
        for field_name, field_type in all_fields:
            assert field_name in search_fields
            if field_type in models.FieldType.exact_types:
                assert suffix_format.format(field_name, 'ne') in search_fields
                if field_type == models.FieldType.status:
                    expected_type = types.request.ActionType
                else:
                    expected_type = graphene.Int
            elif field_type in models.FieldType.range_types:
                suffixes = ['ne', 'gt', 'lt', 'le', 'ge']
                for suffix in suffixes:
                    assert suffix_format.format(field_name, suffix) in \
                        search_fields
                if field_type == models.FieldType.datetime:
                    expected_type = graphene.types.datetime.DateTime
                elif field_type == models.FieldType.decimal:
                    expected_type = types.decimal.Decimal
                elif field_type == models.FieldType.integer:
                    expected_type = graphene.Int
            else:
                # else case covering models.FieldType.text
                expected_type = graphene.String
            if is_input:
                assert isinstance(search_fields[field_name],
                                  graphene.InputField)
            else:
                assert isinstance(search_fields[field_name], graphene.Field)
            assert isinstance(search_fields[field_name].type, graphene.List)
            assert search_fields[field_name].type.of_type == expected_type
        # check that the helper methods are added correctly
        if not is_input:
            assert getattr(SearchType, 'to_storage_search', None) is not None
            assert getattr(SearchType, 'from_storage_search', None) is not None
            assert getattr(SearchType, 'from_input_search', None) is not None


    def test_graphql_to_storage_search(self):
        graphql_search = types.RequestSearch()
        # Start with filtering some exact attributes
        graphql_search.request_id = [1, 2, 3]
        graphql_search.request_id__ne = [4, 5, 6]
        # Now filter some range attributes
        graphql_search.request_timestamp = [
            dt.datetime(2017, 7, 4),
        ]
        graphql_search.request_timestamp__gt = [
            dt.datetime(2016, 10, 31),
        ]
        # Now add a sort in there
        graphql_search.sorts = [
            types.SortToken(key=types.SortKey.payout,
                            direction=types.SortDirection.descending),
            types.SortToken(key=types.SortKey.status,
                            direction=types.SortDirection.descending),
        ]
        store_search = graphql_search.to_storage_search()
        # Create a parallel Search object to compare against
        expected_search = search_filter.Search()
        expected_search.add_filter('request_id', 1, 2, 3)
        expected_search.add_filter(
            'request_id', 4, 5, 6,
            predicate=search_filter.PredicateType.not_equal
        )
        expected_search.add_filter('request_timestamp', dt.datetime(2017, 7, 4))
        expected_search.add_filter(
            'request_timestamp',
            dt.datetime(2016, 10, 31),
            predicate=search_filter.PredicateType.greater
        )
        expected_search.add_sort(
            'payout',
            direction=search_filter.SortDirection.descending
        )
        expected_search.add_sort(
            'status',
            direction=search_filter.SortDirection.descending
        )
        assert store_search == expected_search

    def test_blank_in_search_to_out_search(self):
        out_search = types.RequestSearch.from_input_search(None)
        assert out_search is not None

    def test_in_search_to_out_search(self):
        # Input types are weird and act like dictionaries. Also, the key names
        # are converted back to snake case form camel case.
        in_search = {
            'request_id': [1, 2, 3],
            'request_id__ne': [4, 5, 6],
            'request_timestamp': [
                '2017-07-04T00:00',
            ],
            'request_timestamp__gt': [
                '2016-10-31T00:00',
            ],
            'status': [
                'evaluating',
            ],
            'payout__le': [
                '90000000',
            ],
            'sorts': [
                {
                    'key': 'payout',
                    'direction': 'descending',
                },
                {
                    'key': 'status',
                    'direction': 'descending',
                },
            ],
        }
        out_search = types.RequestSearch.from_input_search(in_search)
        assert out_search.request_id == [1, 2, 3]
        assert out_search.request_id__ne == [4, 5, 6]
        assert out_search.request_timestamp == [
            dt.datetime(2017, 7, 4),
        ]
        assert out_search.request_timestamp__gt == [
            dt.datetime(2016, 10, 31),
        ]
        assert out_search.status == [
            types.ActionType.evaluating,
        ]
        assert out_search.payout__le == [
            decimal.Decimal(90000000),
        ]
        assert out_search.sorts == [
            types.SortToken(key=types.SortKey.payout,
                            direction=types.SortDirection.descending),
            types.SortToken(key=types.SortKey.status,
                            direction=types.SortDirection.descending),
        ]

    def test_storage_to_graphql_search(self):
        # Just reversing test_graphql_to_storage_search
        storage = search_filter.Search()
        storage.add_filter('request_id', 1, 2, 3)
        storage.add_filter(
            'request_id', 4, 5, 6,
            predicate=search_filter.PredicateType.not_equal
        )
        storage.add_filter('request_timestamp', dt.datetime(2017, 7, 4))
        storage.add_filter(
            'request_timestamp',
            dt.datetime(2016, 10, 31),
            predicate=search_filter.PredicateType.greater
        )
        storage.add_sort(
            'payout',
            direction=search_filter.SortDirection.descending
        )
        storage.add_sort(
            'status',
            direction=search_filter.SortDirection.descending
        )
        graphql_search = types.RequestSearch.from_storage_search(storage)
        # Construct a parallel graphql search to compare against
        expected_search = types.RequestSearch()
        expected_search.request_id = [1, 2, 3]
        expected_search.request_id__ne = [4, 5, 6]
        expected_search.request_timestamp = [
            dt.datetime(2017, 7, 4),
        ]
        expected_search.request_timestamp__gt = [
            dt.datetime(2016, 10, 31),
        ]
        expected_search.sorts = [
            types.SortToken(key=types.SortKey.payout,
                            direction=types.SortDirection.descending),
            types.SortToken(key=types.SortKey.status,
                            direction=types.SortDirection.descending),
        ]
        assert expected_search == graphql_search

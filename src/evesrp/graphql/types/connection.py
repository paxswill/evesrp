from __future__ import absolute_import

import collections
import decimal as std_decimal
import itertools

import graphene
import graphene.relay
import graphene.types.datetime
from graphene.utils.str_converters import to_camel_case, to_snake_case
import iso8601
import six

from evesrp import new_models as models
from evesrp import search_filter
from . import decimal
from . import request as types_request


_scalar_field_types = {
    models.FieldType.integer: graphene.Int,
    models.FieldType.datetime: graphene.types.datetime.DateTime,
    models.FieldType.decimal: decimal.Decimal,
    models.FieldType.string: graphene.String,
    models.FieldType.text: graphene.String,
    models.FieldType.ccp_id: graphene.Int,
    models.FieldType.app_id: graphene.Int,
    models.FieldType.status: types_request.ActionType,
    models.FieldType.url: graphene.String,
}


def _create_sort_enum():
    """Create a GraphQL enumerated type for sorting keys."""
    sorts = [(to_camel_case(name), value) for value, name in enumerate(
        itertools.chain(models.Killmail.sorts, models.Request.sorts))]
    return graphene.Enum('SortKey', sorts)


SortKey = _create_sort_enum()


SortDirection = graphene.Enum.from_enum(search_filter.SortDirection)


class BaseSortToken(object):
    """Mixin object implementing common functionality for SortToken and
    InputSortToken.
    """

    def __eq__(self, other):
        if not isinstance(other, BaseSortToken):
            return NotImplemented
        return self.key == other.key and self.direction == other.direction

    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__,
            self.direction,
            self.key
        )


class InputSortToken(graphene.InputObjectType, BaseSortToken):
    """GraphQL input type for one search token.

    Search tokens are defined as a sort key (a field to sort on) and a
    direction.
    """

    key = graphene.InputField(SortKey, required=True)

    direction = graphene.InputField(SortDirection, required=True)


class SortToken(graphene.ObjectType, BaseSortToken):
    """GraphQL output type for sort tokens.

    See :py:class:`~.InputSortToken` for a description of what a sort token is.
    """

    key = graphene.Field(SortKey, required=True)

    direction = graphene.Field(SortDirection, required=True)

    @classmethod
    def from_input(cls, in_dict):
        """Creates a SortToken from a dictionary.

        Primarily used as a way to convert InputSortTokens in dict form.
        """
        # the input dictionary gives us the key and directions as ints, as
        # those are the values for the enums
        key = SortKey.get(in_dict['key'])
        direction = SortDirection.get(in_dict['direction'])
        return cls(key=key, direction=direction)


def _all_field_names(include_original_name=False):
    all_field_types = itertools.chain(
        six.iteritems(models.Request.field_types),
        six.iteritems(models.Killmail.field_types)
    )
    for field_name, field_type in all_field_types:
        if field_type in models.FieldType.exact_types:
            predicates = search_filter.PredicateType.exact_comparisons
        elif field_type in models.FieldType.range_types:
            predicates = search_filter.PredicateType.range_comparisons
        elif field_type == models.FieldType.text:
            predicates = [
                search_filter.PredicateType.equal,
            ]
        for predicate in predicates:
            if predicate != search_filter.PredicateType.equal:
                attr_name = '{}__{}'.format(field_name,
                                            predicate.value)
            else:
                attr_name = field_name
            if include_original_name:
                yield (field_name, attr_name)
            else:
                yield attr_name


def _storage_search_from_graphql_search(self):
    """Create a Storage search instance from this GraphQL search instance.

    This is added as an instance method on dynamically constructed
    RequestSearch types.
    """
    search = search_filter.Search()
    for field_name, attr_name in _all_field_names(True):
        try:
            values = getattr(self, attr_name)
        except AttributeError:
            continue
        else:
            if field_name == attr_name:
                predicate = search_filter.PredicateType.equal
            else:
                predicate_short_name = attr_name[-2:]
                predicate = search_filter.PredicateType(predicate_short_name)
            if field_name.endswith('_timestamp'):
                # Graphene parses ISO8601 strings and defaults to UTC-aware
                # datetimes. We use naive datetimes throughout evesrp, and
                # coparisons between them fail.
                values = [v.replace(tzinfo=None) for v in values]
            search.add_filter(field_name, *values, predicate=predicate)
    # Add the sorts (if any)
    search.clear_sorts()
    try:
        sorts = self.sorts
    except AttributeError:
        pass
    else:
        for token in sorts:
            key_name = to_snake_case(token.key.name)
            search.add_sort(key_name, token.direction)
    return search


def _graphql_search_from_store_search(cls, store_search):
    """Create a GraphQL Search type instance from a
    :py:class:`~evesrp.search_filter.Search` instance.

    This is added as a classmethod to RequestSearch when the type is created.

    :param store_search: The `Search` object to convert.
    :type: :py:class:`evesrp.search_filter.Search`
    """
    graphql_search = cls()
    for field_name, filters in store_search.filters:
        for filter_value, filter_predicate in filters:
            if filter_predicate == search_filter.PredicateType.equal:
                attr_name = field_name
            else:
                attr_name = "{}__{}".format(field_name, filter_predicate.value)
            if not hasattr(graphql_search, attr_name):
                setattr(graphql_search, attr_name, list())
            filter_list = getattr(graphql_search, attr_name)
            filter_list.append(filter_value)
    sorts = []
    for key_string, sort_direction in store_search.sorts:
        sort_key = getattr(SortKey, key_string)
        sorts.append(SortToken(key=sort_key, direction=sort_direction))
    graphql_search.sorts = sorts
    return graphql_search


def _output_search_from_input_search(cls, input_search):
    """Create a RequestSearch for a given InputRequestSearch.

    This is added as a classmethod on RequestSearch when the type is created.

    :type input_search: `evesrp.graphql.types.InputRequestSearch`
    """
    output_search = cls()
    # Because (at least as of now) it's not perticularly well documented, in
    # Graphene input types passed in as arguments are plain old dictionaries
    # with the keys being the original, snake-case names.
    if input_search is not None:
        # Because the Field names are being explicitly given in
        # _create_request_search, we need to manually convert from CamelCase to
        # snake_case.
        converted_input = {to_snake_case(k): v for k, v in
                           six.iteritems(input_search)}
        for field_name, attr_name in _all_field_names(True):
            if attr_name in converted_input:
                try:
                    field_type = models.Request.field_types[field_name]
                except KeyError:
                    try:
                        field_type = models.Killmail.field_types[field_name]
                    except KeyError:
                        # If this is reached, the GraphQL validation failed
                        # somewhere along the line.
                        raise
                # Some types of fields need to be converted to their actual
                # types before going further
                if field_type == models.FieldType.status:
                    # Enum values are converted to ints, even when passed in as
                    # string values.
                    values = [types_request.ActionType.get(v) for v in
                              converted_input[attr_name]]
                else:
                    values = converted_input[attr_name]
                setattr(output_search, attr_name, values)
        if 'sorts' in converted_input:
            output_search.sorts = [SortToken.from_input(t) for t in
                                   input_search['sorts']]
    return output_search


def _search_equals(self, other):
    if not isinstance(other, self.__class__):
        return NotImplemented
    for field_name in self._meta.fields:
        if field_name == 'sorts':
            continue
        # Using sets for all comparisons in here as the order of filter fields
        # is unimportant, but GraphQL only has ordered lists
        try:
            self_value = set(getattr(self, field_name))
        except AttributeError:
            self_value = set()
        try:
            other_value = set(getattr(other, field_name))
        except AttributeError:
            other_value = set()
        if self_value != other_value:
            return False
    # on the other hand, order does matter for sorting
    self_sorts = getattr(self, 'sorts', list())
    other_sorts = getattr(other, 'sorts', list())
    return self_sorts == other_sorts


def _create_request_search(name, is_input_type):
    """Create a GraphQL type for searching over requests.

    The field names and types are generated from
    :py:class:`~.models.request.Request`\'s :py:attr:`~.Request.field_types`
    and :py:attr:~.Request.sorts` class members, as well as the corresponding
    members from :py:class:`~.models.request.Killmails`\. In addition, a
    `from_search` classmethod is added to create an instance of the new search
    type from a :py:class:`~.search_filter.Search`\.

    :param bool is_input_type: Whether to create an input type or output type.
    :rtype: class
    """
    if is_input_type:
        ObjectType = graphene.InputObjectType
        FieldType = graphene.InputField
    else:
        ObjectType = graphene.ObjectType
        FieldType = graphene.Field
    object_fields = collections.OrderedDict()

    all_field_types = itertools.chain(
        six.iteritems(models.Request.field_types),
        six.iteritems(models.Killmail.field_types)
    )
    for field_name, field_type in all_field_types:
        # Skipping 'eq' as a suffix, and use the unsuffixed name instead
        if field_type in models.FieldType.exact_types:
            suffixes = ['ne']
        elif field_type in models.FieldType.range_types:
            suffixes = ['ne', 'gt', 'lt', 'ge', 'le']
        elif field_type == models.FieldType.text:
            suffixes = []
        graphql_scalar = _scalar_field_types[field_type]
        object_fields[field_name] = FieldType(graphene.List(graphql_scalar))
        for suffix in suffixes:
            attribute_name = '{}__{}'.format(field_name, suffix)
            graphql_name = '{}__{}'.format(to_camel_case(field_name), suffix)
            object_fields[attribute_name] = FieldType(
                graphene.List(graphql_scalar),
                name=graphql_name
            )
    # Add the sort field
    if is_input_type:
        object_fields['sorts'] = graphene.InputField(
            graphene.List(InputSortToken))
    else:
        object_fields['sorts'] = graphene.List(SortToken)
    # Add the convenience methods for converting between storage and
    # GraphQL search types. InputTypes are basically fancy dicts (in graphene's
    # eyes), so no sense adding these methods to them.
    if not is_input_type:
        object_fields['to_storage_search'] = \
            _storage_search_from_graphql_search
        object_fields['from_storage_search'] = classmethod(
            _graphql_search_from_store_search)
        object_fields['from_input_search'] = classmethod(
            _output_search_from_input_search)
        object_fields['__eq__'] = _search_equals
    return type(name, (ObjectType, ), object_fields)


InputRequestSearch = _create_request_search('InputRequestSearch', True)


RequestSearch = _create_request_search('RequestSearch', False)


class RequestConnection(graphene.relay.Connection):

    class Meta(object):
        node = types_request.Request

    total_count = graphene.Int(required=True)

    total_payout = graphene.Field(decimal.Decimal, required=True)

    search = graphene.Field(RequestSearch, required=True)

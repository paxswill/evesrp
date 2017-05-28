import collections
import itertools

import graphene
import graphene.types.datetime
import graphene.relay
import six

from evesrp import new_models as models
from . import decimal
from . import request as types_request


_scalar_field_types = {
    models.util.FieldType.integer: graphene.Int,
    # TODO Add datetime
    models.util.FieldType.decimal: decimal.Decimal,
    models.util.FieldType.string: graphene.String,
    models.util.FieldType.text: graphene.String,
    models.util.FieldType.ccp_id: graphene.Int,
    models.util.FieldType.app_id: graphene.Int,
    models.util.FieldType.status: types_request.ActionType,
    models.util.FieldType.url: graphene.String,
}


def _field_types_to_object_fields(field_types, is_input_type):
    """Convert a map of model fields to GraphQL fields.

    `field_types` is a :py:class:`dict` with the keys being the string names of
    the fields, and the values being :py:class:`~evesrp.models.util.FieldType`
    instances. An ordered dictionary is preferable, but not necessary. Whether
    to use normal 'output' :py:class:`graphene.Field` or
    :py:class:`graphene.InputField` is determined by `is_input_type`. If the
    :py:class:`~.FieldType` is unknown or unhandled, it is silently ignored. An
    ordered dict is returned with the keys still being the names of the fields,
    but the values are GraphQL fields.

    :param dict field_types: The fields to convert.
    :param bool is_input_type: Whether to use input field types.
    :rtype: :py:class:`collections.OrderedDict`
    """
    object_fields = collections.OrderedDict()
    if is_input_type:
        FieldType = graphene.InputField
    else:
        FieldType = graphene.Field
    for field_name, field_type in six.iteritems(field_types):
        try:
            scalar_type = _scalar_field_types[field_type]
        except KeyError:
            pass
        else:
            object_fields[field_name] = FieldType(graphene.List(scalar_type))
    return object_fields


def _graphql_search_from_store_search(cls, store_search):
    """Create a GraphQL Search type instance from a
    :py:class:`~evesrp.search_filter.Search` instance.

    This is added as a classmethod to dynamically constructed Search types.

    :param store_search: The `Search` object to convert.
    :type: :py:class:`evesrp.search_filter.Search`
    """
    # TODO: Fix so sorts get converted properly
    search = cls()
    for field, filters in store_search:
        setattr(search, field, list(filters))
    return search


def _create_sort_enum():
    """Create a GraphQL enumerated type for sorting keys."""
    sorts = [(name, value) for value, name in enumerate(
        itertools.chain(models.Killmail.sorts, models.Request.sorts))]
    return graphene.Enum('SortKey', sorts)


SortKey = _create_sort_enum()


class SortDirection(graphene.Enum):
    """GraphQL enum for which direction to sort."""

    ascending = 0

    descending = 1


class InputSortToken(graphene.InputObjectType):
    """GraphQL input type for one search token.

    Search tokens are defined as a sort key (a field to sort on) and a
    direction.
    """

    key = graphene.InputField(SortKey, required=True)

    direction = graphene.InputField(SortDirection, required=True)


class SortToken(graphene.ObjectType):
    """GraphQL output type for sort tokens.

    See :py:class:`~.InputSortToken` for a description of what a sort token is.
    """

    key = graphene.Field(SortKey, required=True)

    direction = graphene.Field(SortDirection, required=True)


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
    else:
        ObjectType = graphene.ObjectType
    request_fields = _field_types_to_object_fields(models.Request.field_types,
                                                   is_input_type)
    killmail_fields = _field_types_to_object_fields(
        models.Killmail.field_types, is_input_type)
    object_fields = collections.OrderedDict()
    object_fields.update(killmail_fields)
    object_fields.update(request_fields)
    # Add the sort field
    if is_input_type:
        object_fields['sorts'] = graphene.InputField(
            graphene.List(InputSortToken))
    else:
        object_fields['sorts'] = graphene.List(SortToken)
    # Add the convenience classmethod for creating a GraphQL type from an
    # application type
    object_fields['from_search'] = classmethod(
        _graphql_search_from_store_search)
    return type(name, (ObjectType, ), object_fields)


InputRequestSearch = _create_request_search('InputRequestSearch', True)


RequestSearch = _create_request_search('RequestSearch', False)


class RequestConnection(graphene.relay.Connection):

    class Meta(object):
        node = types_request.Request

    total_count = graphene.Int(required=True)

    total_payout = graphene.Field(decimal.Decimal, required=True)

    search = graphene.Field(RequestSearch, required=True)

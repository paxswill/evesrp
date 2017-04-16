import base64
import collections
import itertools

import graphene
import six

from . import decimal, types
from evesrp import new_models as models


_scalar_field_types = {
    models.util.FieldType.integer: graphene.Int,
    # TODO Add datetime
    models.util.FieldType.decimal: decimal.Decimal,
    models.util.FieldType.string: graphene.String,
    models.util.FieldType.text: graphene.String,
    models.util.FieldType.ccp_id: graphene.Int,
    models.util.FieldType.app_id: graphene.Int,
    models.util.FieldType.status: types.ActionType,
    models.util.FieldType.url: graphene.String,
}


def _field_types_to_object_fields(field_types, input_type):
    object_fields = collections.OrderedDict()
    if input_type:
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
    search = cls()
    for field, filters in store_search:
        setattr(search, field, list(filters))
    return search


def _create_killmail_search(input_type):
    if input_type:
        ObjectType = graphene.InputObjectType
    else:
        ObjectType = graphene.ObjectType
    object_fields = _field_types_to_object_fields(models.Killmail.field_types,
                                                  input_type)
    object_fields['from_search'] = classmethod(
        _graphql_search_from_store_search)
    return type('KillmailSearch',
                (ObjectType, ),
                object_fields)


InputKillmailSearch = _create_killmail_search(True)


KillmailSearch = _create_killmail_search(False)


def _create_request_search(input_type):
    if input_type:
        ObjectType = graphene.InputObjectType
    else:
        ObjectType = graphene.ObjectType
    request_fields = _field_types_to_object_fields(models.Request.field_types,
                                                   input_type)
    killmail_fields = _field_types_to_object_fields(
        models.Killmail.field_types)
    object_fields = collections.OrderedDict()
    object_fields.update(killmail_fields)
    object_fields.update(request_fields)
    object_fields['from_search'] = classmethod(
        _graphql_search_from_store_search)
    return type('RequestSearch',
                (ObjectType, ),
                object_fields)


InputRequestSearch = _create_request_search(True)


RequestSearch = _create_request_search(False)


def _create_sort_enum():
    sorts = [(name, value) for value, name in enumerate(
        itertools.chain(models.Killmail.sorts, models.Request.sorts))]
    return graphene.Enum('SortKey', sorts)


SortKey = _create_sort_enum()


class SortDirection(graphene.Enum):

    ascending = 0

    descending = 1


class InputSortToken(graphene.InputObjectType):

    key = graphene.InputField(SortKey, required=True)

    direction = graphene.InputField(SortDirection, required=True)


class InputSort(graphene.InputObjectType):

    sorts = graphene.InputField(graphene.List(InputSortToken), required=True)


class SortToken(graphene.ObjectType):

    key = graphene.Field(SortKey, required=True)

    direction = graphene.Field(SortDirection, required=True)


class Sort(graphene.ObjectType):

    sorts = graphene.NonNull(graphene.List(SortToken))


class EdgeNodes(graphene.Union):

    class Meta(object):
        types = (types.Killmail,
                 types.Request)


class Edge(graphene.ObjectType):

    node = graphene.Field(EdgeNodes)

    cursor = graphene.ID(required=True)


class PageInfo(graphene.ObjectType):

    end_cursor = graphene.ID(required=True)

    has_next = graphene.Boolean()


class PagerInterface(graphene.Interface):

    edges = graphene.List(Edge)

    total_count = graphene.Int()

    page_info = graphene.Field(PageInfo)

    sorts = graphene.List(lambda: Sort)


class KillmailPager(graphene.ObjectType):

    class Meta(object):
        interfaces = (PagerInterface, )

    search = KillmailSearch


class RequestPager(graphene.ObjectType):

    class Meta(object):
        interfaces = (PagerInterface, )

    total_payout = decimal.Decimal()

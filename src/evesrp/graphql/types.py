import collections
import itertools

import graphene
import graphene.types.datetime
import graphene.types.json
import graphene.relay
import six

from evesrp import new_models as models
from evesrp import search_filter
from . import decimal


def get_node(cls, id, context, info):
    return cls(id=int(id))


def simple_get_node(klass):
    klass.get_node = classmethod(get_node)
    return klass


class Named(graphene.Interface):

    name = graphene.String(required=True)


class Entity(graphene.Interface):

    permissions = graphene.NonNull(graphene.List(lambda: Permission))


@simple_get_node
class User(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, Named, Entity)

    admin = graphene.Boolean(required=True)

    groups = graphene.List(lambda: Group)

    notes = graphene.List(lambda: Note)

    requests = graphene.List(lambda: Request)

    characters = graphene.List(lambda: Character)

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_, name=model.name, admin=model.admin)


@simple_get_node
class Group(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, Named, Entity)

    users = graphene.NonNull(graphene.List(User))

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_, name=model.name)


class Identity(graphene.Interface):

    provider_uuid = graphene.ID(required=True)

    provider_key = graphene.ID(required=True)

    extra = graphene.types.json.JSONString()


class UserIdentity(graphene.ObjectType):

    class Meta(object):
        interfaces = (Identity, )

    user = graphene.Field(User)


class GroupIdentity(graphene.ObjectType):

    class Meta(object):
        interfaces = (Identity, )

    group = Group()


class IdentityUnion(graphene.Union):

    class Meta(object):
        types = (UserIdentity, GroupIdentity)


@simple_get_node
class Division(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, Named)

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_, name=model.name)


PermissionType = graphene.Enum.from_enum(models.PermissionType)


class Permission(graphene.ObjectType):

    permission = PermissionType()

    entity = graphene.NonNull(Entity)

    division = graphene.NonNull(Division)

    @classmethod
    def from_model(cls, model):
        # Turns out graphene Enums aren't quite API compatible with standard
        # library Enums
        permission_type = getattr(PermissionType, model.type_.name)
        assert permission_type is not None
        return cls(permission=permission_type,
                   division=Division(id=model.division_id),
                   entity=model.entity_id)


@simple_get_node
class Note(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    subject = graphene.NonNull(User)

    submitter = graphene.NonNull(User)

    contents = graphene.String(required=True)

    timestamp = graphene.types.datetime.DateTime(required=True)

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_,
                   subject=User(id=model.subject_id),
                   submitter=User(id=model.submitter_id),
                   contents=model.contents,
                   timestamp=model.timestamp)


@simple_get_node
class Character(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, Named)

    user = graphene.Field(User)

    ccp_id = graphene.Int(required=True)

    @classmethod
    def from_model(cls, model):
        user = User(id=model.user_id)
        return cls(id=model.id_, name=model.name, user=user)


@simple_get_node
class Killmail(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    killmail_id = graphene.Int(required=True)

    user = graphene.NonNull(User)

    character = graphene.NonNull(Character)

    # TODO: redo the various CCP *_ids to custom CCP object types
    corporation_id = graphene.Int(required=True)

    alliance_id = graphene.Int()

    system_id = graphene.Int(required=True)

    constellation_id = graphene.Int(required=True)

    region_id = graphene.Int(required=True)

    type_id = graphene.Int(required=True)

    timestamp = graphene.types.datetime.DateTime(required=True)

    url = graphene.String(required=True)

    @classmethod
    def from_model(cls, model):
        user = User(id=model.user_id)
        character = Character(id=model.character_id)
        return cls(id=model.id_,
                   user=user,
                   character=character,
                   corporation_id=model.corporation_id,
                   alliance_id=model.alliance_id,
                   system_id=model.system_id,
                   constellation_id=model.constellation_id,
                   region_id=model.region_id,
                   type_id=model.type_id,
                   timestamp=model.timestamp,
                   url=model.url)


ActionType = graphene.Enum.from_enum(models.ActionType)


@simple_get_node
class Action(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    action_type = graphene.NonNull(ActionType)

    timestamp = graphene.types.datetime.DateTime(required=True)

    contents = graphene.String()

    user = graphene.NonNull(User)

    @classmethod
    def from_model(cls, model):
        user = User(id=model.user_id)
        action_type = getattr(ActionType, model.type_.name)
        return cls(id=model.id_,
                   action_type=action_type,
                   timestamp=model.timestamp,
                   contents=model.contents,
                   user=user)


ModifierType = graphene.Enum.from_enum(models.ModifierType)


@simple_get_node
class Modifier(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    modifier_type = graphene.NonNull(ModifierType)

    value = graphene.NonNull(decimal.Decimal)

    note = graphene.String()

    user = graphene.NonNull(User)

    timestamp = graphene.types.datetime.DateTime(required=True)

    void = graphene.Boolean(required=True)

    void_user = User()

    void_timestamp = graphene.types.datetime.DateTime()

    @classmethod
    def from_model(cls, model):
        user = User(id=model.user_id)
        if model.is_void:
            void_user = User(id=model.void_user_id)
            void_timetamp = model.void_timestamp
        else:
            void_user = None
            void_timestamp = None
        modifier_type = getattr(ModifierType, model.type_.name)
        return cls(id=model.id_,
                   modifier_type=modifier_type,
                   value=model.value,
                   note=model.note,
                   user=user,
                   timestamp=model.timestamp,
                   void_user=void_user,
                   void_timestamp=void_timestamp)


@simple_get_node
class Request(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    details = graphene.String()

    killmail = graphene.NonNull(Killmail)

    division = graphene.NonNull(Division)

    timestamp = graphene.types.datetime.DateTime(required=True)

    status = ActionType(required=True)

    base_payout = graphene.NonNull(decimal.Decimal)

    payout = graphene.NonNull(decimal.Decimal)

    actions = graphene.List(Action)

    modifiers = graphene.List(Modifier)

    def resolve_status(self, args, context, info):
        return self.status.name

    def resolve_actions(self, args, context, info):
        store = context['store']
        action_models = store.get_actions(self.id)
        return [Action.from_model(a) for a in action_models]

    def resolve_modifiers(self, args, context, info):
        store = context['store']
        modifier_models = store.get_modifiers(self.id)
        return [Modifier.from_model(m) for m in modifier_models]

    @classmethod
    def from_model(cls, model):
        status = getattr(ActionType, model.status.name)
        return cls(id=model.id_,
                   details=model.details,
                   killmail=Killmail(id=model.killmail_id),
                   division=Division(id=model.division_id),
                   timestamp=model.timestamp,
                   status=status,
                   base_payout=model.base_payout,
                   payout=model.payout)


_scalar_field_types = {
    models.util.FieldType.integer: graphene.Int,
    # TODO Add datetime
    models.util.FieldType.decimal: decimal.Decimal,
    models.util.FieldType.string: graphene.String,
    models.util.FieldType.text: graphene.String,
    models.util.FieldType.ccp_id: graphene.Int,
    models.util.FieldType.app_id: graphene.Int,
    models.util.FieldType.status: ActionType,
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

    total_count = graphene.Int(required=True)

    total_payout = graphene.Field(decimal.Decimal, required=True)

    search = graphene.Field(RequestSearch, required=True)

    class Meta(object):
        node = Request

import graphene
import graphene.types.datetime
import graphene.types.json
import graphene.relay

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

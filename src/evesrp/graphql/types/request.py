import graphene
import graphene.relay
import graphene.types.datetime

from evesrp import new_models as models
import evesrp.graphql.types
from . import util, decimal, ccp


@util.simple_get_node
class Character(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named)

    user = graphene.Field('evesrp.graphql.types.authorization.User')

    ccp_id = graphene.Int(required=True)

    @classmethod
    def from_model(cls, model):
        user = evesrp.graphql.types.User(id=model.user_id)
        return cls(id=model.id_, name=model.name, user=user)


@util.simple_get_node
class Killmail(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    killmail_id = graphene.Int(required=True)

    user = graphene.NonNull('evesrp.graphql.types.authorization.User')

    character = graphene.NonNull(Character)

    corporation = graphene.Field(ccp.CcpType, required=True)

    alliance = graphene.Field(ccp.CcpType, required=True)

    system = graphene.Field(ccp.CcpType, required=True)

    constellation = graphene.Field(ccp.CcpType, required=True)

    region = graphene.Field(ccp.CcpType, required=True)

    type = graphene.Field(ccp.CcpType, required=True)

    timestamp = graphene.types.datetime.DateTime(required=True)

    url = graphene.String(required=True)

    requests = graphene.Field(
        graphene.List('evesrp.graphql.types.request.Request'), required=True)

    @classmethod
    def from_model(cls, model):
        user = evesrp.graphql.types.User(id=model.user_id)
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


@util.simple_get_node
class Action(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    action_type = graphene.NonNull(ActionType)

    timestamp = graphene.types.datetime.DateTime(required=True)

    contents = graphene.String()

    user = graphene.NonNull('evesrp.graphql.types.authorization.User')

    @classmethod
    def from_model(cls, model):
        user = evesrp.graphql.types.User(id=model.user_id)
        action_type = getattr(ActionType, model.type_.name)
        return cls(id=model.id_,
                   action_type=action_type,
                   timestamp=model.timestamp,
                   contents=model.contents,
                   user=user)


ModifierType = graphene.Enum.from_enum(models.ModifierType)


@util.simple_get_node
class Modifier(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    modifier_type = graphene.NonNull(ModifierType)

    value = graphene.NonNull(decimal.Decimal)

    note = graphene.String()

    user = graphene.NonNull('evesrp.graphql.types.authorization.User')

    timestamp = graphene.types.datetime.DateTime(required=True)

    void = graphene.Boolean(required=True)

    void_user = graphene.NonNull('evesrp.graphql.types.authorization.User')

    void_timestamp = graphene.types.datetime.DateTime()

    @classmethod
    def from_model(cls, model):
        user = evesrp.graphql.types.User(id=model.user_id)
        if model.is_void:
            void_user = evesrp.graphql.types.User(id=model.void_user_id)
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


@util.simple_get_node
class Request(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, )

    details = graphene.String()

    killmail = graphene.NonNull(Killmail)

    division = graphene.NonNull('evesrp.graphql.types.authorization.Division')

    timestamp = graphene.types.datetime.DateTime(required=True)

    status = ActionType(required=True)

    base_payout = graphene.NonNull(decimal.Decimal)

    payout = graphene.NonNull(decimal.Decimal)

    actions = graphene.List(Action)

    modifiers = graphene.List(Modifier)

    @classmethod
    def from_model(cls, model):
        status = getattr(ActionType, model.status.name)
        return cls(id=model.id_,
                   details=model.details,
                   killmail=Killmail(id=model.killmail_id),
                   division=evesrp.graphql.types.Division(
                       id=model.division_id),
                   timestamp=model.timestamp,
                   status=status,
                   base_payout=model.base_payout,
                   payout=model.payout)

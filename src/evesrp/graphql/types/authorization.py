import graphene
import graphene.relay
import graphene.types.datetime
import graphene.types.json

from evesrp import new_models as models
from . import util


class Entity(graphene.Interface):

    permissions = graphene.NonNull(graphene.List(lambda: Permission))


@util.simple_get_node
class User(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named, Entity)

    admin = graphene.Boolean(required=True)

    groups = graphene.List(lambda: Group)

    notes = graphene.List(lambda: Note)

    requests = graphene.List(lambda: types_request.Request)

    characters = graphene.List(lambda: types_request.Character)

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_, name=model.name, admin=model.admin)


@util.simple_get_node
class Group(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named, Entity)

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


@util.simple_get_node
class Division(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named)

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


@util.simple_get_node
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


# Bit of a hack/workaround to resolve circular dependencies
from . import request as types_request

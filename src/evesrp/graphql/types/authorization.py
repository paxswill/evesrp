import graphene
import graphene.relay
import graphene.types.datetime
import graphene.types.json

from evesrp import new_models as models
from . import util


class Entity(graphene.Interface):

    permissions = graphene.NonNull(
        graphene.List('evesrp.graphql.types.authorization.Permission'))


@util.simple_get_node
class User(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named, Entity)

    admin = graphene.Boolean(required=True)

    groups = graphene.NonNull(
        graphene.List('evesrp.graphql.types.authorization.Group'))

    notes = graphene.NonNull(
        graphene.List('evesrp.graphql.types.authorization.Note'))

    requests = graphene.NonNull(
        graphene.List('evesrp.graphql.types.request.Request'))

    requests_connection = graphene.relay.ConnectionField(
        'evesrp.graphql.types.connection.RequestConnection')

    characters = graphene.NonNull(
        graphene.List('evesrp.graphql.types.request.Character'))

    @classmethod
    def from_model(cls, model):
        return cls(id=model.id_, name=model.name, admin=model.admin)


@util.simple_get_node
class Group(graphene.ObjectType):

    class Meta(object):
        interfaces = (graphene.relay.Node, util.Named, Entity)

    users = graphene.NonNull(graphene.List(User))

    # TODO Add a users_connection

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

    # TODO: Add a permissions field of some kind maybe?

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

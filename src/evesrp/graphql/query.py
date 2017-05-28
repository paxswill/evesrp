import functools

import graphene
import graphene.relay

from evesrp.graphql import types
from evesrp import new_models as models
from evesrp import storage


class Query(graphene.ObjectType):

    node = graphene.relay.Node.Field()

    identity = graphene.Field(
        types.IdentityUnion,
        uuid=graphene.Argument(
            graphene.ID,
            required=True
        ),
        key=graphene.Argument(
            graphene.ID,
            required=True
        )
    )

    users = graphene.Field(
        graphene.NonNull(graphene.List(types.User)),
        group_id=graphene.ID()
    )

    groups = graphene.Field(graphene.List(types.Group), user_id=graphene.ID())

    divisions = graphene.Field(graphene.List(types.Division))

    permission = graphene.Field(
        types.Permission,
        entity_id=graphene.Argument(
            graphene.ID,
            required=True
        ),
        division_id=graphene.Argument(
            graphene.ID,
            required=True
        ),
        permission_type=graphene.Argument(
            types.PermissionType,
            required=True
        )
    )

    permissions = graphene.Field(
        graphene.List(types.Permission),
        entity_ids=graphene.Argument(
            graphene.List(graphene.NonNull(graphene.ID))
        ),
        division_ids=graphene.Argument(
            graphene.List(graphene.NonNull(graphene.ID))
        ),
        permission_types=graphene.Argument(
            graphene.List(graphene.NonNull(types.PermissionType))
        )
    )

    notes = graphene.Field(
        graphene.NonNull(graphene.List(types.Note)),
        subject_id=graphene.Argument(
            graphene.ID,
            required=True
        )
    )

    character = graphene.Field(
        types.Character,
        ccp_id=graphene.Argument(
            graphene.Int,
            required=True
        )
    )

    killmail = graphene.Field(
        types.Killmail,
        ccp_id=graphene.Argument(
            graphene.Int,
            required=True
        )
    )

    actions = graphene.Field(
        graphene.NonNull(graphene.List(types.Action)),
        request_id=graphene.Argument(
            graphene.ID,
            required=True
        )
    )

    modifiers = graphene.Field(
        graphene.NonNull(graphene.List(types.Modifier)),
        request_id=graphene.Argument(
            graphene.ID,
            required=True
        ),
        include_void=graphene.Argument(
            graphene.Boolean,
            default_value=True,
        ),
        modifier_type=graphene.Argument(
            types.ModifierType
        )
    )

    request = graphene.Field(
        types.Request,
        killmail_id=graphene.Argument(
            graphene.ID,
            required=True
        ),
        division_id=graphene.Argument(
            graphene.ID,
            required=True
        )
    )

    requests_connection = graphene.relay.ConnectionField(
        types.RequestConnection,
        search=graphene.Argument(types.InputRequestSearch)
    )


schema = graphene.Schema(query=Query)

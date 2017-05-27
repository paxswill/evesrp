import functools

import graphene
import graphene.relay

from evesrp.graphql import types
from evesrp import new_models as models
from evesrp import storage


class Query(graphene.ObjectType):

    node = graphene.relay.Node.Field()

    identity = graphene.Field(types.IdentityUnion,
                              uuid=graphene.Argument(
                                  graphene.ID,
                                  required=True
                              ),
                              key=graphene.Argument(
                                  graphene.ID,
                                  required=True
                              ))

    user = graphene.Field(types.User,
                          id=graphene.Argument(
                              graphene.ID,
                              required=True
                          ))

    users = graphene.Field(
        graphene.NonNull(graphene.List(types.User)),
        group_id=graphene.ID())

    group = graphene.Field(types.Group,
                           id=graphene.Argument(
                               graphene.ID,
                               required=True
                           ))

    groups = graphene.Field(graphene.List(types.Group), user_id=graphene.ID())

    division = graphene.Field(types.Division, 
                              id=graphene.Argument(
                                  graphene.ID,
                                  required=True
                              ))

    divisions = graphene.Field(graphene.List(types.Division))

    permission = graphene.Field(types.Permission,
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
                                ))

    permissions = graphene.Field(graphene.List(types.Permission),
                                 entity_id=graphene.Argument(
                                     graphene.ID
                                 ),
                                 division_id=graphene.Argument(
                                     graphene.ID
                                 ),
                                 permission_type=graphene.Argument(
                                     types.PermissionType
                                 ))

    notes = graphene.Field(graphene.List(types.Note),
                           subject_id=graphene.Argument(
                               graphene.ID,
                               required=True
                           ))

    character = graphene.Field(types.Character,
                               id=graphene.Argument(
                                   graphene.ID,
                                   required=False
                               ),
                               ccp_id=graphene.Argument(
                                   graphene.Int,
                                   required=False
                               ))

    killmail = graphene.Field(types.Killmail,
                              id=graphene.Argument(
                                  graphene.ID,
                                  required=False
                              ),
                              ccp_id=graphene.Argument(
                                  graphene.Int,
                                  required=False
                              ))

    actions = graphene.Field(graphene.List(types.Action),
                             request_id=graphene.Argument(
                                 graphene.Int,
                                 required=True
                             ))

    modifiers = graphene.Field(graphene.List(types.Modifier),
                               request_id=graphene.Argument(
                                   graphene.Int,
                                   required=True
                               ),
                               include_void=graphene.Argument(
                                   graphene.Boolean,
                                   default_value=True,
                               ),
                               modifier_type=graphene.Argument(
                                   types.ModifierType
                               ))

    request = graphene.Field(types.Request,
                             id=graphene.Int(),
                             killmail_id=graphene.Int(),
                             division_id=graphene.Int())

    requests_connection = graphene.relay.ConnectionField(
        types.SearchableRequestConnection,
        search=graphene.Argument(types.InputRequestSearch)
    )


schema = graphene.Schema(query=Query)

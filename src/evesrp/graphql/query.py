import functools

import graphene

from evesrp.graphql import types, pagination
from evesrp import graphql
from evesrp import new_models as models
from evesrp import storage


def resolve_store_and_args(func):
    """Utility decorator to simplify writing resolvers using a store."""
    @functools.wraps(func)
    def inner(self, args, context, info):
        store = context['store']
        return func(self, store, **args)
    return inner


# TODO: Add a time range input field
_killmail_fields = {
    'user': graphene.Int(),
    'corporation': graphene.Int(),
    'alliance': graphene.Int(),
    'system': graphene.Int(),
    'constellation': graphene.Int(),
    'region': graphene.Int(),
    'item_type': graphene.Int(),
}


# TODO: Add Decimal Input field
_request_fields = {
    'killmail': graphene.Int(),
    'division': graphene.Int(),
    'status': types.ActionType(),
}


_all_fields = dict()
_all_fields.update(_killmail_fields)
_all_fields.update(_request_fields)


class Query(graphene.ObjectType):

    identity = graphene.Field(types.IdentityUnion,
                              uuid=graphene.Argument(
                                  graphene.ID,
                                  required=True
                              ),
                              key=graphene.Argument(
                                  graphene.ID,
                                  required=True
                              ))

    @resolve_store_and_args
    def resolve_identity(self, store, uuid, key):
        identity_kwargs = {}
        try:
            identity = store.get_authn_user(uuid, key)
            identity_kwargs['user'] = types.User(id=identity.user_id)
            IdentityType = types.UserIdentity
        except storage.NotFoundError:
            identity = store.get_authn_group(uuid, key)
            identity_kwargs['group'] = types.Group(id=identity.group_id)
            IdentityType = types.GroupIdentity
        identity_kwargs.update(
            provider_uuid=identity.provider_uuid,
            provider_key=identity.provider_key,
            extra=identity.extra_data)
        return IdentityType(**identity_kwargs)

    user = graphene.Field(types.User,
                          id=graphene.Argument(
                              graphene.Int,
                              required=True
                          ))

    @resolve_store_and_args
    def resolve_user(self, store, id):
        try:
            user_model = store.get_user(id)
        except storage.NotFoundError:
            return None
        else:
            return types.User.from_model(user_model)

    users = graphene.Field(graphene.List(types.User), group_id=graphene.Int())

    @resolve_store_and_args
    def resolve_users(self, store, group_id=None):
        return [types.User.from_model(u) for u in store.get_users(group_id)]

    group = graphene.Field(types.Group,
                           id=graphene.Argument(
                               graphene.Int,
                               required=True
                           ))

    @resolve_store_and_args
    def resolve_group(self, store, id):
        try:
            group_model = store.get_group(id)
        except storage.NotFoundError:
            return None
        else:
            return types.Group.from_model(group_model)

    groups = graphene.Field(graphene.List(types.Group), user_id=graphene.Int())

    @resolve_store_and_args
    def resolve_groups(self, store, user_id=None):
        return [types.Group.from_model(g) for g in store.get_groups(user_id)]

    division = graphene.Field(types.Division, id=graphene.Int())

    @resolve_store_and_args
    def get_division(self, store, id):
        try:
            division_model = store.get_division(id)
        except storage.NotFoundError:
            return None
        else:
            return types.Division.from_model(division_model)

    divisions = graphene.Field(graphene.List(types.Division))

    @resolve_store_and_args
    def get_divisions(self, store):
        return [types.Division.from_model(d) for d in store.get_divisions()]

    permission = graphene.Field(types.Permission,
                                entity_id=graphene.Argument(
                                    graphene.Int,
                                    required=True
                                ),
                                division_id=graphene.Argument(
                                    graphene.Int,
                                    required=True
                                ),
                                permission_type=graphene.Argument(
                                    types.PermissionType,
                                    required=True
                                ))

    @resolve_store_and_args
    def resolve_permission(self, store, **args):
        permissions = list(store.get_permissions(**args))
        if not permissions:
            return None
        return types.Permission.from_model(permissions[0])

    permissions = graphene.Field(graphene.List(types.Permission),
                                 entity_id=graphene.Argument(
                                     graphene.Int
                                 ),
                                 division_id=graphene.Argument(
                                     graphene.Int
                                 ),
                                 permission_type=graphene.Argument(
                                     types.PermissionType
                                 ))

    @resolve_store_and_args
    def resolve_permissions(self, store, **args):
        return [types.Permission.from_model(p)
                for p in store.get_permissions(**args)]

    notes = graphene.Field(graphene.List(types.Note),
                           subject_id=graphene.Argument(
                               graphene.Int,
                               required=True
                           ))

    @resolve_store_and_args
    def resolve_notes(self, store, subject_id):
        return [types.Note.from_model(n) for n in store.get_notes(subject_id)]

    character = graphene.Field(types.Character,
                               id=graphene.Argument(
                                   graphene.Int,
                                   required=True
                               ))

    @resolve_store_and_args
    def resolve_character(self, store, id):
        try:
            character_model = store.get_character(id)
        except storage.NotFoundError:
            return None
        else:
            return types.Character.from_model(character_model)

    killmail = graphene.Field(types.Killmail,
                              id=graphene.Argument(
                                  graphene.Int,
                                  required=True
                              ))

    @resolve_store_and_args
    def resolve_killmail(self, store, id):
        try:
            killmail_model = store.get_killmail(id)
        except storage.NotFoundError:
            return None
        else:
            return types.Killmail.from_model(killmail_model)

    killmails = graphene.Field(graphene.List(types.Killmail),
                               args=_killmail_fields)

    @resolve_store_and_args
    def resolve_killmails(self, store, **args):
        # TODO: Add filtering
        pass

    killmails_pager = graphene.Field(pagination.Pager,
                                     first=graphene.Int(),
                                     after_cursor=graphene.ID(),
                                     args=_killmail_fields)

    actions = graphene.Field(graphene.List(types.Action),
                             request_id=graphene.Argument(
                                 graphene.Int,
                                 required=True
                             ))

    @resolve_store_and_args
    def resolve_actions(self, store, request_id):
        return [types.Action.from_model(a)
                for a in store.get_actions(request_id)]

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

    @resolve_store_and_args
    def resolve_modifiers(self, store, request_id, include_void,
                          modifier_type=None):
        void_arg = None if include_void else False
        modifier_models = store.get_modifiers(request_id, 
                                              void=void_arg,
                                              type_=modifier_type)
        return [types.Modifier.from_model(m) for m in modifier_models]

    request = graphene.Field(types.Request,
                             id=graphene.Int(),
                             killmail_id=graphene.Int(),
                             division_id=graphene.Int())

    @resolve_store_and_args
    def resolve_request(self, store, **args):
        try:
            request_model = store.get_request(**args)
        except TypeError:
            # TODO: Check to see if we can raise an error here instead of just
            # returning null
            return None
        else:
            return types.Request.from_model(request_model)

    requests = graphene.Field(graphene.List(types.Request),
                              args=_all_fields)

    requests_pager = graphene.Field(pagination.Pager,
                                    first=graphene.Int(),
                                    after_cursor=graphene.ID(),
                                    args=_all_fields)


schema = graphene.Schema(query=Query)

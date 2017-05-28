import base64
import itertools
import uuid

from graphql_relay import from_global_id
import six

from evesrp import new_models as models
from evesrp import search_filter, storage
from . import types


class Resolver(object):

    def __init__(self, store, user):
        self.store = store
        self.user = user

    def resolve(self, next, source, args, context, info):
        field_name = info.field_name
        model_name = info.parent_type.name
        interface_names = [getattr(i, 'name')
                           for i in info.parent_type.interfaces]
        # Skip trying to resolve for Node.id
        if 'Node' in interface_names and field_name == 'id':
            return next(source, args, context, info)
        # Start with a resolver for that object's field
        func_name_template = "resolve_{}_field_{}"
        object_func_name = func_name_template.format(model_name.lower(),
                                                     field_name.lower())
        func_names = [object_func_name]
        # Then check interface resolvers for that field
        func_names.extend([func_name_template.format(interface.lower(),
                                                     field_name.lower())
                           for interface in interface_names])
        # Then check for a catchall resolver for that object
        func_names.append("resolve_{}_fields".format(model_name.lower()))
        # Then catchalls for the interfaces
        func_names.extend(["resolve_{}_fields".format(interface.lower())
                           for interface in interface_names])
        for func_name in func_names:
            if hasattr(self, func_name):
                resolve_func = getattr(self, func_name)
                break
        else:
            resolve_func = next
        return resolve_func(source, args, context, info)

    # Query

    # Not implementing resolve_query_field_node as we're going to rely on
    # graphene.relay's get_node magic and then rely on the sub-types'
    # resolvers.

    def resolve_query_field_identity(self, source, args, context, info):
        provider_uuid = uuid.UUID(args['uuid'])
        key = args['key']
        identity_kwargs = {}
        try:
            identity = self.store.get_authn_user(provider_uuid, key)
            identity_kwargs['user'] = types.User(id=identity.user_id)
            IdentityType = types.UserIdentity
        except storage.NotFoundError:
            identity = self.store.get_authn_group(provider_uuid, key)
            identity_kwargs['group'] = types.Group(id=identity.group_id)
            IdentityType = types.GroupIdentity
        identity_kwargs.update(
            provider_uuid=identity.provider_uuid,
            provider_key=identity.provider_key,
            extra=identity.extra_data)
        return IdentityType(**identity_kwargs)

    @staticmethod
    def _check_id(relay_id, type_names):
        if isinstance(type_names, six.string_types):
            type_names = [type_names]
        id_type, type_id = from_global_id(relay_id)
        if id_type not in type_names:
            if len(type_names) == 1:
                message = ("Given a '{}' ID instead of a "
                           "'{}' ID ({}).").format(
                               id_type, type_names[0], relay_id)
            else:
                message = ("Given a '{}' ID instead of one of the following: "
                           "{} ({}).").format(
                               id_type, str(type_names), relay_id)
            raise Exception(message)
        return int(type_id)

    def resolve_query_field_users(self, source, args, context, info):
        group_id = args.get('group_id')
        if group_id is not None:
            group_id = self._check_id(group_id, 'Group')
        user_ids = [u.id_ for u in self.store.get_users(group_id)]
        user_ids.sort()
        return [types.User(id=uid) for uid in user_ids]

    def resolve_query_field_groups(self, source, args, context, info):
        user_id = args.get('user_id')
        if user_id is not None:
            user_id = self._check_id(user_id, 'User')
        group_ids = [g.id_ for g in self.store.get_groups(user_id)]
        group_ids.sort()
        return [types.Group(id=gid) for gid in group_ids]

    def resolve_query_field_divisions(self, source, args, context, info):
        division_ids = [d.id_ for d in self.store.get_divisions()]
        division_ids.sort()
        return [types.Division(id=did) for did in division_ids]

    def resolve_query_field_permission(self, source, args, context, info):
        entity_id = self._check_id(args['entity_id'], ['Entity', 'User',
                                                       'Group'])
        division_id = self._check_id(args['division_id'], 'Division')
        permission_type = models.PermissionType[args['permission_type']]
        permissions = list(self.store.get_permissions(
            entity_id=entity_id, division_id=division_id,
            type_=permission_type))
        if not permissions:
            return None
        return types.Permission.from_model(permissions[0])

    def resolve_query_field_permissions(self, source, args, context, info):
        entity_ids = args.get('entity_ids')
        if entity_ids is not None:
            entity_ids = [self._check_id(eid, ['Entity', 'User', 'Group'])
                          for eid in entity_ids]
        division_ids = args.get('division_ids')
        if division_ids is not None:
            division_ids = [self._check_id(did, 'Division')
                            for did in division_ids]
        permission_types = args.get('permission_types')
        if permission_types is not None:
            permission_types = [models.PermissionType[p]
                                for p in permission_types]
        permissions = list(self.store.get_permissions(
            entity_id=entity_ids,
            division_id=division_ids,
            type_=permission_types
        ))
        return [types.Permission.from_model(p) for p in permissions]

    def resolve_query_field_notes(self, source, args, context, info):
        subject_id = self._check_id(args['subject_id'], 'User')
        return [types.Note.from_model(n)
                for n in self.store.get_notes(subject_id)]

    def resolve_query_field_character(self, source, args, context, info):
        ccp_id = args['ccp_id']
        try:
            character_model = self.store.get_character(ccp_id)
        except storage.NotFoundError:
            return None
        else:
            return types.Character.from_model(character_model)

    def resolve_query_field_killmail(self, source, args, context, info):
        ccp_id = args['ccp_id']
        try:
            killmail_model = self.store.get_killmail(ccp_id)
        except storage.NotFoundError:
            return None
        else:
            return types.Killmail.from_model(killmail_model)

    def resolve_query_field_actions(self, source, args, context, info):
        return [types.Action.from_model(a)
                for a in self.store.get_actions(request_id)]

    def resolve_query_field_modifiers(self, source, args, context, info):
        modifier_type = args.get('modifier_type')
        void_arg = None if args['include_void'] else False
        modifier_models = self.store.get_modifiers(args['request_id'], 
                                                   void=void_arg,
                                                   type_=modifier_type)
        return [types.Modifier.from_model(m) for m in modifier_models]

    def resolve_query_field_request(self, source, args, context, info):
        killmail_id = self._check_id(args['killmailId'], 'Killmail')
        division_id = self._check_id(args['divisionId'], 'Division')
        try:
            request_model = self.store.get_request(killmail_id=killmail_id,
                                                   division_id=division_id)
        except TypeError:
            # TODO: Check to see if we can raise an error here instead of just
            # returning null
            return None
        else:
            return types.Request(id=request_model.id_)

    def resolve_query_field_requests(self, source, args, context, info):
        limit = args.get('limit')
        after_cursor = args.get('after_cursor')
        input_search = args.get('search')
        sort = args.get('sort')
        store_search = search_filter.Search()
        if input_search is not None:
            field_names = itertools.chain(
                six.iterkeys(models.Request.field_types),
                six.iterkeys(models.Killmail.field_types))
            for field_name in field_names:
                values = getattr(input_search, field_name)
                if len(values):
                    store_search.add(field_name, *values)
        if sort is not None:
            pass
        request_models = self.store.filter_requests(store_search)
        # Sanitize input
        if limit is not None and limit < 0:
            limit = None
        if after_cursor is not None:
            decoded = base64.b64decode(after_cursor)
            # cursor is of the form "offset###"
            offset = int(decoded[6:])
        else:
            offset = 0
        # TODO Fix this so it returns Edges and Pager and stuff correctly
        return itertools.islice(
            [types.Request.from_model(r) for r in request_models],
            offset, limit)

    # Named

    def resolve_named_field_name(self, source, args, context, info):
        model_name = type(source).__name__.lower()
        getter_name = 'get_{}'.format(model_name)
        getter = getattr(self.store, getter_name)
        model = getter(source.id)
        return model.name

    # Entity

    def resolve_entity_field_permissions(self, source, args, context, info):
        return [types.Permission.from_model(p)
                for p in self.store.get_permissions(entity_id=source.id)]

    # User

    def resolve_user_field_admin(self, source, args, context, info):
        model = self.store.get_user(source.id)
        return model.admin

    def resolve_user_field_groups(self, source, args, context, info):
        group_models = self.store.get_groups(source.id)
        group_ids = [g.id_ for g in group_models]
        group_ids.sort()
        return [types.Group(id=gid) for gid in group_ids]

    def resolve_user_field_notes(self, source, args, context, info):
        return [types.Note.from_model(n)
                for n in self.store.get_notes(source.id)]

    def resolve_user_field_requests(self, source, args, context, info):
        search = search_filter.Search()
        search.add('user_id', source.id)
        # TODO: sorting on request_id is broken
        search.set_sort('request_id')
        request_models = self.store.filter_requests(search)
        return [types.Request.from_model(r) for r in request_models]

    def resolve_user_field_permissions(self, source, args, context, info):
        permission_models = set()
        permission_models.update(self.store.get_permissions(
            entity_id=source.id))
        group_models = self.store.get_groups(source.id)
        for group in group_models:
            permission_models.update(
                self.store.get_permissions(entity_id=group.id_))
        return [types.Permission.from_model(p) for p in permission_models]

    def resolve_user_field_characters(self, source, args, context, info):
        character_models = self.store.get_characters(source.id)
        character_ids = [c.id_ for c in character_models]
        character_ids.sort()
        return [types.Character(id=cid) for cid in character_ids]

    # Group

    def resolve_group_field_users(self, source, args, context, info):
        return [types.User.from_model(u)
                for u in self.store.get_users(source.id)]

    # Permission

    def resolve_permission_field_entity(self, source, args, context, info):
        # self.entity is stored as an int when created with
        # Permission.from_model
        entity = self.store.get_entity(source.entity)
        if isinstance(entity, models.User):
            return types.User.from_model(entity)
        else:
            return types.Group.from_model(entity)

    def resolve_permission_field_permission(self, source, args, context, info):
        # graphene requires you to return the name of the enum member, not just
        # the enum member. wat.
        return source.permission.name

    # Note

    def resolve_note_fields(self, source, args, context, info):
        model = self.store.get_note(source.id)
        note = types.Note.from_model(model)
        return getattr(note, info.field_name)

    # Character

    def resolve_character_field_name(self, source, args, context, info):
        character_model = self.store.get_character(source.id)
        return character_model.name

    def resolve_character_field_ccpid(self, source, args, context, info):
        return source.id

    def resolve_character_field_user(self, source, args, context, info):
        character_model = self.store.get_character(source.id)
        if character_model.user_id is None:
            return None
        return types.User(id=character_model.user_id)

    # Action

    def resolve_action_fields(self, source, args, context, info):
        model = self.store.get_action(source.id)
        return getattr(model, info.field_name)

    def resolve_action_field_actiontype(self, source, args, context, info):
        model = self.store.get_action(source.id)
        # Just throwing it out there, graphql-core's handling of enumerated
        # types is inconsistent with how it seems everybody else uses them, and
        # tracking down errors is hampered by their poor logging/exception
        # handling. Ugh.
        return model.type_.value

    def resolve_action_field_user(self, source, args, context, info):
        model = self.store.get_action(source.id)
        return types.User(model.user_id)

    # Modifier

    def resolve_modifier_fields(self, source, args, context, info):
        model = self.store.get_modifier(source.id)
        value = getattr(model, info.field_name)
        return value

    def resolve_modifier_field_modifiertype(self, source, args, context, info):
        # See the comment in resolve_action_field_actiontype about handling
        # enums. It's terrible.
        model = self.store.get_modifier(source.id)
        type_ = getattr(types.ModifierType, model.type_.name)
        return type_.value

    def resolve_modifier_field_user(self, source, args, context, info):
        model = self.store.get_modifier(source.id)
        return types.User(model.user_id)

    def resolve_modifier_field_voiduser(self, source, args, context, info):
        model = self.store.get_modifier(source.id)
        return types.User(model.void_user_id)

    def resolve_modifier_field_voidtimestamp(self, source, args, context,
                                             info):
        model = self.store.get_modifier(source.id)
        return model.void_timestamp

    def resolve_modifier_field_void(self, source, args, context, info):
        model = self.store.get_modifier(source.id)
        return model.is_void

    # Request

    def resolve_request_fields(self, source, args, context, info):
        model = self.store.get_request(source.id)
        if info.field_name == 'basePayout':
            field_name = 'base_payout'
        else:
            field_name = info.field_name
        return getattr(model, field_name)

    def resolve_request_field_status(self, source, args, context, info):
        # More graphene enum silliness
        model = self.store.get_request(source.id)
        return model.status.value

    def resolve_request_field_division(self, source, args, context, info):
        model = self.store.get_request(source.id)
        return types.Division(id=model.division_id)

    def resolve_request_field_killmail(self, source, args, context, info):
        model = self.store.get_request(source.id)
        return types.Killmail(id=model.killmail_id)

    def resolve_request_field_actions(self, source, args, context, info):
        action_models = self.store.get_actions(source.id)
        return [types.Action.from_model(a) for a in action_models]

    def resolve_request_field_modifiers(self, source, args, context, info):
        modifier_models = self.store.get_modifiers(source.id)
        return [types.Modifier.from_model(m) for m in modifier_models]

    # Killmail

    def resolve_killmail_field_killmailid(self, source, args, context, info):
        return source.id

    def resolve_killmail_field_user(self, source, args, context, info):
        model = self.store.get_killmail(source.id)
        return types.User(id=model.user_id)

    def resolve_killmail_field_character(self, source, args, context, info):
        model = self.store.get_killmail(source.id)
        return types.Character(id=model.character_id)

    def resolve_killmail_fields(self, source, args, context, info):
        """Resolve CCP-derived info like location, membership and type from
        here.
        """
        model = self.store.get_killmail(source.id)
        if info.field_name in {'corporation', 'alliance', 'system',
                               'constellation', 'region', 'type'}:
            named_id = "{}_id".format(info.field_name)
            id_ = getattr(model, named_id)
            # Get the name
            getter_name = "get_{}".format(info.field_name)
            getter = getattr(self.store, getter_name)
            getter_args = {named_id: id_}
            name = getter(**getter_args)['name']
            return types.CcpType(id=id_, name=name)
        else:
            return getattr(model, info.field_name)

    def resolve_killmail_field_requests(self, source, args, context, info):
        request_models = self.store.get_requests(source.id)
        request_ids = [r.id_ for r in request_models]
        request_ids.sort()
        return [types.Request(id=rid) for rid in request_ids]

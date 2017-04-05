import datetime as dt
from decimal import Decimal
import functools
import itertools

import six

from . import BaseStore, CachingCcpStore, errors
from evesrp import new_models as models
from evesrp import search_filter


class MemoryStore(CachingCcpStore, BaseStore):

    def __init__(self, **kwargs):
        self._data = {}
        for key in ('authn_users', 'authn_groups', 'divisions',
                    'users', 'groups', 'group_members', 'killmails',
                    'requests', 'actions', 'modifiers', 'characters', 'notes'):
            self._data[key] = dict()
        for key in ('permissions', ):
            self._data[key] = set()
        super(MemoryStore, self).__init__(**kwargs)

    # Authentication

    def _entity_storage(self, entity_type):
        return self._data['authn_' + entity_type + 's']

    def _get_authn_entity(self, entity_type, provider_uuid, provider_key):
        # Use a tuple as the key in the authn_entity dict
        entity_key = (provider_uuid, str(provider_key))
        try:
            entity_data = self._entity_storage(entity_type)[entity_key]
        except KeyError as key_exc:
            not_found = errors.NotFoundError(
                'Authenticated{}'.format(entity_type.capitalize()),
                '({}, {})'.format(provider_uuid, provider_key))
            six.raise_from(not_found, key_exc)
        entity_dict = dict(entity_data)
        entity_dict['provider_uuid'] = provider_uuid
        entity_dict['provider_key'] = provider_key
        if entity_type == 'user':
            return models.AuthenticatedUser.from_dict(entity_dict)
        elif entity_type == 'group':
            return models.AuthenticatedGroup.from_dict(entity_dict)

    def _add_authn_entity(self, entity_type, entity_id, provider_uuid,
                          provider_key, extra_data=None, **kwargs):
        entity_key = (provider_uuid, str(provider_key))
        if extra_data is None:
            extra_data = {}
        extra_data.update(kwargs)
        entity_data = {
            (entity_type + '_id'): entity_id,
            'extra_data': extra_data,
        }
        self._entity_storage(entity_type)[entity_key] = entity_data
        entity_dict = dict(entity_data)
        entity_dict['provider_uuid'] = provider_uuid
        entity_dict['provider_key'] = provider_key
        if entity_type == 'user':
            return models.AuthenticatedUser.from_dict(entity_dict)
        elif entity_type == 'group':
            return models.AuthenticatedGroup.from_dict(entity_dict)

    def _save_authn_entity(self, entity_type, authn_entity):
        entity_key = (authn_entity.provider_uuid,
                      str(authn_entity.provider_key))
        id_name = entity_type + '_id'
        self._entity_storage(entity_type)[entity_key] = {
            id_name: getattr(authn_entity, id_name),
            'extra_data': authn_entity.extra_data,
        }

    def get_authn_user(self, provider_uuid, provider_key):
        return self._get_authn_entity('user', provider_uuid, provider_key)

    def add_authn_user(self, user_id, provider_uuid, provider_key,
                       extra_data=None, **kwargs):
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        return self._add_authn_entity('user', user_id, provider_uuid,
                                      provider_key, extra_data, **kwargs)

    def save_authn_user(self, authn_user):
        self._save_authn_entity('user', authn_user)

    def get_authn_group(self, provider_uuid, provider_key):
        return self._get_authn_entity('group', provider_uuid, provider_key)

    def add_authn_group(self, group_id, provider_uuid, provider_key,
                        extra_data=None, **kwargs):
        if group_id not in self._data['groups']:
            raise errors.NotFoundError('group', group_id)
        return self._add_authn_entity('group', group_id, provider_uuid,
                                      provider_key, extra_data, **kwargs)

    def save_authn_group(self, authn_group):
        self._save_authn_entity('group', authn_group)

    # Shared

    def _get_from_dict(self, data_key, id_, from_dict):
        try:
            data = self._data[data_key][id_]
        except KeyError as key_exc:
            # data keys are pluralized, so drop the final char (should be 's')
            not_found = errors.NotFoundError(data_key[:-1], id_)
            six.raise_from(not_found, key_exc)
        return from_dict(data)

    def _get_next_id(self, data_key):
        new_id = len(self._data[data_key])
        while new_id in self._data[data_key]:
            new_id += 1
        return new_id

    def _add_to_dict(self, data_key, from_dict, data):
        if 'id' not in data:
            data['id'] = self._get_next_id(data_key)
        self._data[data_key][data['id']] = data
        return from_dict(data)

    # Divisions

    def get_division(self, division_id):
        return self._get_from_dict('divisions', division_id,
                                   models.Division.from_dict)

    def get_divisions(self, division_ids=None):
        if division_ids is None:
            divisions_data = six.itervalues(self._data['divisions'])
        else:
            divisions_data = [self._data['divisions'].get(d_id) for d_id in
                              division_ids]
        divisions_data = filter(lambda d: d is not None, divisions_data)
        divisions = [models.Division.from_dict(d_data) for d_data in
                     divisions_data]
        return divisions

    def add_division(self, name):
        return self._add_to_dict('divisions', models.Division.from_dict,
                                 {'name': name})

    def save_division(self, division):
        self._data['divisions'][division.id_] = {
            'name': division.name,
            'id': division.id_,
        }

    # Permissions

    def get_permissions(self, **kwargs):
        # entity_id, division_id, types, type_
        filter_sets = {
            'entity_id': set(),
            'division_id': set(),
            'type_': set(),
        }
        for key in six.iterkeys(filter_sets):
            if isinstance(kwargs.get(key), (int, models.PermissionType)):
                filter_sets[key].add(kwargs[key])
            elif key in kwargs:
                filter_sets[key].update(kwargs[key])

        def filter_func(perm):
            for key, value in six.iteritems(filter_sets):
                if len(value) > 0 and getattr(perm, key) not in value:
                    return False
            return True
        return filter(filter_func, self._data['permissions'])

    def add_permission(self, division_id, entity_id, type_):
        if division_id not in self._data['divisions']:
            raise errors.NotFoundError('division', division_id)
        if entity_id not in self._data['users'] and \
                entity_id not in self._data['groups']:
            raise errors.NotFoundError('entity', entity_id)
        permission = models.Permission(division_id, entity_id, type_)
        self._data['permissions'].add(permission)
        return permission

    def remove_permission(self, *args, **kwargs):
        if len(args) == 1:
            permission = args[0]
        elif 'permission' in kwargs:
            permission = kwargs['permission']
        elif len(args) == 3:
            permission = models.Permission(division_id=args[0],
                                           entity_id=args[1],
                                           type_=args[2])
        else:
            permission = models.Permission(**kwargs)
        self._data['permissions'].discard(permission)

    # Users and Groups

    def get_user(self, user_id):
        return self._get_from_dict('users', user_id, models.User.from_dict)

    def get_users(self, group_id):
        member_ids = self._data['group_members'].get(group_id, set())
        users_data = [self._data['users'][uid] for uid in member_ids]
        return {models.User.from_dict(data) for data in users_data}

    def add_user(self, name, is_admin=False):
        return self._add_to_dict('users', models.User.from_dict,
                                 {
                                     'name': name,
                                     'admin': is_admin,
                                 })

    def save_user(self, user):
        # Only names and admin-ness can change
        if user.id_ not in self._data['users']:
            raise errors.NotFoundError('user', user.id_)
        user_data = self._data['users'][user.id_]
        user_data['admin'] = user.admin
        user_data['name'] = user.name

    def get_group(self, group_id):
        return self._get_from_dict('groups', group_id, models.Group.from_dict)

    def get_groups(self, user_id):
        membership = self._data['group_members']
        group_ids = {gid for gid, uids in six.iteritems(membership) if
                     user_id in uids}
        groups_data = [self._data['groups'][gid] for gid in group_ids]
        return {models.Group.from_dict(data) for data in groups_data}

    def add_group(self, name):
        return self._add_to_dict('groups', models.Group.from_dict,
                                 {'name': name})

    def save_group(self, group):
        # Only group names can change
        if group.id_ not in self._data['groups']:
            raise errors.NotFoundError('group', group.id_)
        group_data = self._data['groups'][group.id_]
        group_data['name'] = group.name

    def associate_user_group(self, user_id, group_id):
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        if group_id not in self._data['groups']:
            raise errors.NotFoundError('group', group_id)
        membership = self._data['group_members'].get(group_id, set())
        membership.add(user_id)
        self._data['group_members'][group_id] = membership

    def disassociate_user_group(self, user_id, group_id):
        membership = self._data['group_members'].get(group_id, set())
        membership.discard(user_id)
        self._data['group_members'][group_id] = membership

    # Killmails

    def get_killmail(self, killmail_id):
        return self._get_from_dict('killmails', killmail_id,
                                   models.Killmail.from_dict)

    def add_killmail(self, **kwargs):
        user_id = kwargs['user_id']
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        try:
            character_id = kwargs['character_id']
        except KeyError as key_exc:
            type_error = TypeError("missing required argument (character_id).")
            six.raise_from(type_error, key_exc)
        if character_id not in self._data['characters']:
            raise errors.NotFoundError('character', character_id)
        killmail_data = dict(kwargs)
        killmail_data['id'] = killmail_data.pop('id_')
        # Create the killmail first to make sure everything is there
        killmail = models.Killmail.from_dict(killmail_data)
        self._data['killmails'][killmail_data['id']] = killmail_data
        return killmail

    # Requests

    def get_request(self, request_id=None, killmail_id=None, division_id=None):
        if request_id is not None:
            request_data = self._data['requests'].get(request_id)
        elif killmail_id is not None and division_id is not None:
            for possible_match in six.itervalues(self._data['requests']):
                if possible_match['killmail_id'] == killmail_id and \
                        possible_match['division_id'] == division_id:
                    request_data = possible_match
                    break
            else:
                request_data = None
        else:
            raise TypeError("Either request_id or both killmail_id and"
                            "division_id must be given.")
        if request_data is None:
            if request_id is not None:
                identitifer = str(request_id)
            else:
                identitifer = '({}, {})'.format(killmail_id, division_id)
            raise errors.NotFoundError('request', identitifer)
        else:
            return models.Request.from_dict(request_data)

    def get_requests(self, killmail_id):
        requests_data = [km for km in six.itervalues(self._data['requests'])
                         if km['killmail_id'] == killmail_id]
        return [models.Request.from_dict(r) for r in requests_data]

    def add_request(self, killmail_id, division_id, details=u''):
        # Check that there's a killmail and division for this request
        if killmail_id not in self._data['killmails']:
            raise errors.NotFoundError('killmail', killmail_id)
        if division_id not in self._data['divisions']:
            raise errors.NotFoundError('division', division_id)
        request_id = self._get_next_id('requests')
        request_data = {
            'id': request_id,
            'killmail_id': killmail_id,
            'division_id': division_id,
            'details': details,
            'timestamp': dt.datetime.utcnow(),
            'base_payout': Decimal(0),
            'payout': Decimal(0),
            'status': models.ActionType.evaluating,
        }
        self._data['requests'][request_id] = request_data
        return models.Request.from_dict(request_data)

    def save_request(self, request):
        try:
            request_data = self._data['requests'][request.id_]
        except KeyError as key_exc:
            not_found = errors.NotFoundError('request', request.id_)
            six.raise_from(not_found, key_exc)
        # Only a few things are allowed to change on requests
        for attr in ('details', 'status', 'base_payout', 'payout'):
            request_data[attr] = getattr(request, attr)

    # Request Actions

    def get_action(self, action_id):
        return self._get_from_dict('actions', action_id,
                                   models.Action.from_dict)

    def get_actions(self, request_id):
        actions_data = [act for act in six.itervalues(self._data['actions'])
                        if act['request_id'] == request_id]
        return [models.Action.from_dict(a) for a in actions_data]

    def add_action(self, request_id, type_, user_id, contents=u''):
        if request_id not in self._data['requests']:
            raise errors.NotFoundError('request', request_id)
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        return self._add_to_dict('actions', models.Action.from_dict,
                                 {
                                     'type': type_,
                                     'timestamp': dt.datetime.utcnow(),
                                     'contents': contents,
                                     'user_id': user_id,
                                     'request_id': request_id,
                                 })

    # Request Modifiers

    def get_modifier(self, modifier_id):
        return self._get_from_dict('modifiers', modifier_id,
                                   models.Modifier.from_dict)

    def get_modifiers(self, request_id, void=None, type_=None):
        modifiers_data = [mod for mod in
                          six.itervalues(self._data['modifiers'])
                          if mod['request_id'] == request_id]

        def void_filter(modifier):
            if void is not None:
                return (modifier['void'] is not None) == void
            return True

        def type_filter(modifier):
            if type_ is not None:
                return modifier['type'] == type_
            return True
        modifiers_data = filter(void_filter, modifiers_data)
        modifiers_data = filter(type_filter, modifiers_data)
        return [models.Modifier.from_dict(m) for m in modifiers_data]

    def add_modifier(self, request_id, user_id, type_, value, note=u''):
        if request_id not in self._data['requests']:
            raise errors.NotFoundError('request', request_id)
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        return self._add_to_dict('modifiers', models.Modifier.from_dict,
                                 {
                                     'type': type_,
                                     'value': value,
                                     'note': note,
                                     'timestamp': dt.datetime.utcnow(),
                                     'user_id': user_id,
                                     'request_id': request_id,
                                     'void': None,
                                 })

    def void_modifier(self, modifier_id, user_id):
        if modifier_id not in self._data['modifiers']:
            raise errors.NotFoundError('modifier', modifier_id)
        else:
            modifier_data = self._data['modifiers'][modifier_id]
            if modifier_data['void'] is not None:
                raise errors.VoidedModifierError(modifier_id)
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        # modifier_data is set if the modifier_id is valid. if it's not valid,
        # an exception has already been raised.
        modifier_data['void'] = {
            'user_id': user_id,
            'timestamp': dt.datetime.utcnow(),
        }

    # Filtering

    def filter_requests(self, filters):
        requests_and_killmails = []
        for request_data in six.itervalues(self._data['requests']):
            request = models.Request.from_dict(request_data)
            killmail = self.get_killmail(request.killmail_id)
            if filters.matches(request, killmail):
                requests_and_killmails.append((request, killmail))
        # Helper sorting key function

        def sort_key(request_killmail, key):
            request, killmail = request_killmail
            if key in models.Request.sorts:
                obj = request
            elif key in models.Killmail.sorts:
                obj = killmail
            if key.endswith('_name'):
                # Get the name from the ID
                base_name = sort_key[:-5]
                id_attribute = base_name + '_id'
                id_value = getattr(obj, id_attribute)
                getter = getattr(self, 'get_' + base_name)
                response = getter(**{id_attribute: id_value})
                try:
                    return response['name']
                except KeyError:
                    return response.name
            elif key.endswith('_timestamp'):
                return getattr(obj, 'timestamp')
            else:
                return getattr(obj, key)

        # Now sort the requests
        for key, direction in reversed(list(filters.sorts)):
            key_func = functools.partial(sort_key, key=key)
            reversed_ = direction != search_filter.SortDirection.ascending
            requests_and_killmails.sort(key=key_func, reverse=reversed_)
        return [request for request, killmail in requests_and_killmails]

    # Characters

    def get_character(self, character_id):
        return self._get_from_dict('characters', character_id,
                                   models.Character.from_dict)

    def get_characters(self, user_id):
        return {models.Character.from_dict(c)
                for c in six.itervalues(self._data['characters'])
                if c['user_id'] == user_id}


    def add_character(self, user_id, character_id, character_name):
        if user_id not in self._data['users']:
            raise errors.NotFoundError('user', user_id)
        return self._add_to_dict('characters', models.Character.from_dict,
                                 {
                                     'user_id': user_id,
                                     'id': character_id,
                                     'name': character_name,
                                 })

    def save_character(self, character):
        if character.id_ not in self._data['characters']:
            raise errors.NotFoundError('character', character.id_)
        character_data = self._data['characters'][character.id_]
        character_data['name'] = character.name
        character_data['user_id'] = character.user_id

    # User Notes

    def get_notes(self, subject_id):
        if subject_id not in self._data['users']:
            raise errors.NotFoundError('user', subject_id)
        notes_data = self._data['notes'].get(subject_id, [])
        return [models.Note.from_dict(n) for n in notes_data]

    def add_note(self, subject_id, submitter_id, contents):
        notes = self._data['notes']
        # Inefficient, but it's a toy storage implementation to ai in
        # development.
        note_ids = {n['id'] for user_notes in six.itervalues(notes)
                    for n in user_notes}
        next_id = len(note_ids)
        while next_id in note_ids:
            next_id += 1
            break
        if subject_id not in notes:
            notes[subject_id] = []
        note_data = {
            'id': next_id,
            'submitter_id': submitter_id,
            'subject_id': subject_id,
            'timestamp': dt.datetime.utcnow(),
            'contents': contents,
        }
        notes[subject_id].append(note_data)
        return models.Note.from_dict(note_data)

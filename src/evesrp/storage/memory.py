import datetime as dt
from decimal import Decimal
import itertools

import six

from . import BaseStore, CachingCcpStore
from evesrp import new_models as models


class MemoryStore(BaseStore, CachingCcpStore):

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
        entity_data = self._entity_storage(entity_type).get(entity_key)
        if entity_data is None:
            return {
                u'result': None,
                u'errors': [
                    'not found',
                ],
            }
            return entity_data
        entity_dict = dict(entity_data)
        entity_dict['provider_uuid'] = provider_uuid
        entity_dict['provider_key'] = provider_key
        if entity_type == 'user':
            return {
                u'result': models.AuthenticatedUser.from_dict(entity_dict),
            }
        elif entity_type == 'group':
            return {
                u'result': models.AuthenticatedGroup.from_dict(entity_dict),
            }

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
            return {
                u'result': models.AuthenticatedUser.from_dict(entity_dict),
            }
        elif entity_type == 'group':
            return {
                u'result': models.AuthenticatedGroup.from_dict(entity_dict),
            }

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
            return {
                u'result': None,
                u'errors': [
                    u"User ID #{} not found".format(user_id),
                ],
            }
        return self._add_authn_entity('user', user_id, provider_uuid,
                                      provider_key, extra_data, **kwargs)

    def save_authn_user(self, authn_user):
        self._save_authn_entity('user', authn_user)

    def get_authn_group(self, provider_uuid, provider_key):
        return self._get_authn_entity('group', provider_uuid, provider_key)

    def add_authn_group(self, group_id, provider_uuid, provider_key,
                        extra_data=None, **kwargs):
        if group_id not in self._data['groups']:
            return {
                u'result': None,
                u'errors': [
                    u"Group ID #{} not found".format(group_id),
                ],
            }
        return self._add_authn_entity('group', group_id, provider_uuid,
                                      provider_key, extra_data, **kwargs)

    def save_authn_group(self, authn_group):
        self._save_authn_entity('group', authn_group)

    # Shared

    def _get_from_dict(self, data_key, id_, from_dict):
        data = self._data[data_key].get(id_)
        if data is None:
            return {
                u'result': None,
                u'errors': [
                    u"{} ID #{} not found".format(data_key[:-1].capitalize(),
                                                  id_),
                ],
            }
        model = from_dict(data)
        return {
            u'result': model,
        }

    def _get_next_id(self, data_key):
        new_id = len(self._data[data_key])
        while new_id in self._data[data_key]:
            new_id += 1
        return new_id

    def _add_to_dict(self, data_key, from_dict, data):
        if 'id' not in data:
            data['id'] = self._get_next_id(data_key)
        self._data[data_key][data['id']] = data
        model = from_dict(data)
        return {
            u'result': model,
        }

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
        return {
            u'result': divisions,
        }

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
        return {
            u'result': set(filter(filter_func, self._data['permissions'])),
        }

    def add_permission(self, division_id, entity_id, type_):
        errors = []
        if division_id not in self._data['divisions']:
            errors.append(u"Division ID #{} not found".format(division_id))
        if entity_id not in self._data['users'] and \
                entity_id not in self._data['groups']:
            errors.append(u"Entity ID #{} not found".format(entity_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
        permission = models.Permission(division_id, entity_id, type_)
        self._data['permissions'].add(permission)
        return {
            u'result': permission,
        }

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
        users = {models.User.from_dict(data) for data in users_data}
        return {
            u'result': users,
        }

    def add_user(self, name, is_admin=False):
        return self._add_to_dict('users', models.User.from_dict,
                                 {
                                     'name': name,
                                     'admin': is_admin,
                                 })

    def get_group(self, group_id):
        return self._get_from_dict('groups', group_id, models.Group.from_dict)

    def get_groups(self, user_id):
        membership = self._data['group_members']
        group_ids = {gid for gid, uids in six.iteritems(membership) if
                     user_id in uids}
        groups_data = [self._data['groups'][gid] for gid in group_ids]
        groups = {models.User.from_dict(data) for data in groups_data}
        return {
            u'result': groups,
        }

    def add_group(self, name):
        return self._add_to_dict('groups', models.Group.from_dict,
                                 {'name': name})

    def associate_user_group(self, user_id, group_id):
        errors = []
        if user_id not in self._data['users']:
            errors.append(u"User ID #{} not found".format(user_id))
        if group_id not in self._data['groups']:
            errors.append(u"Group ID #{} not found".format(group_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
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
        errors = []
        user_id = kwargs['user_id']
        if user_id not in self._data['users']:
            errors.append(u"User ID #{} not found".format(user_id))
        character_id = kwargs['character_id']
        if character_id not in self._data['characters']:
            errors.append(u"Character ID #{} not found".format(character_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
        killmail_data = dict(kwargs)
        killmail_data['id'] = killmail_data.pop('id_')
        # Creaate the killmail first to make sure everything is there
        killmail = models.Killmail.from_dict(killmail_data)
        self._data['killmails'][killmail_data['id']] = killmail_data
        return {
            u'result': killmail,
        }

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
            raise ValueError("Either request_id or both killmail_id and"
                             "division_id must be given.")
        if request_data is None:
            return {
                u'result': None,
                u'errors': [
                    'not found',
                ],
            }
        else:
            return {
                u'result': models.Request.from_dict(request_data)
            }

    def get_requests(self, killmail_id):
        requests_data = [km for km in six.itervalues(self._data['requests'])
                         if km['killmail_id'] == killmail_id]
        requests = [models.Request.from_dict(r) for r in requests_data]
        return {
            u'result': requests,
        }

    def add_request(self, killmail_id, division_id, details=u''):
        # Check that there's a killmail and division for this request
        errors = []
        if killmail_id not in self._data['killmails']:
            errors.append(u"Killmail ID #{} not found".format(killmail_id))
        if division_id not in self._data['divisions']:
            errors.append(u"Division ID #{} not found".format(division_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
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
        return {
            u'result': models.Request.from_dict(request_data)
        }

    def save_request(self, request):
        # Only a few things are allowed to change on requests
        try:
            request_data = self._data['requests'][request.id_]
        except KeyError:
            return {
                u'errors': [
                    "Request ID {} not found".format(request.id_),
                ],
            }
        for attr in ('details', 'status', 'base_payout', 'payout'):
            request_data[attr] = getattr(request, attr)

    # Request Actions

    def get_action(self, action_id):
        return self._get_from_dict('actions', action_id,
                                   models.Action.from_dict)

    def get_actions(self, request_id):
        actions_data = [act for act in six.itervalues(self._data['actions'])
                        if act['request_id'] == request_id]
        actions = [models.Action.from_dict(a) for a in actions_data]
        return {
            u'result': actions,
        }

    def add_action(self, request_id, type_, user_id, contents=u''):
        errors = []
        if request_id not in self._data['requests']:
            errors.append(u"Request ID #{} not found".format(request_id))
        if user_id not in self._data['users']:
            errors.append(u"User ID# {} not found".format(user_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
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
        modifiers = [models.Modifier.from_dict(m) for m in modifiers_data]
        return {
            u'result': modifiers,
        }

    def add_modifier(self, request_id, user_id, type_, value, note=u''):
        errors = []
        if request_id not in self._data['requests']:
            errors.append(u"Request ID #{} not found".format(request_id))
        if user_id not in self._data['users']:
            errors.append(u"User ID# {} not found".format(user_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
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
        errors = []
        if modifier_id not in self._data['modifiers']:
            errors.append(u"Modifier ID #{} not found".format(modifier_id))
        else:
            modifier_data = self._data['modifiers'][modifier_id]
            if modifier_data['void'] is not None:
                errors.append("Modifier ID #{} is already void".format(
                    modifier_id))
        if user_id not in self._data['users']:
            errors.append(u"User ID# {} not found".format(user_id))
        if errors:
            return {
                u'result': None,
                u'errors': errors,
            }
        # modifier_data is set if the modifier_id is valid. if it's not valid,
        # the 'if errors:' return would have already caused us to exit.
        modifier_data['void'] = {
            'user_id': user_id,
            'timestamp': dt.datetime.utcnow(),
        }

    # Filtering

    def filter_requests(self, filters):
        raise NotImplementedError

    # Characters

    def get_character(self, character_id):
        return self._get_from_dict('characters', character_id,
                                   models.Character.from_dict)

    def add_character(self, user_id, character_id, character_name):
        if user_id not in self._data['users']:
            return {
                u'result': None,
                u'errors': [
                    u"User ID# {} not found".format(user_id),
                ],
            }
        return self._add_to_dict('characters', models.Character.from_dict,
                                 {
                                     'user_id': user_id,
                                     'id': character_id,
                                     'name': character_name,
                                 })

    def save_character(self, character):
        if character.id_ not in self._data['characters']:
            return {
                u'result': None,
                u'errors': [
                    u"Character ID# {} not found".format(user_id),
                ],
            }
        character_data = self._data['characters'][character.id_]
        character_data['name'] = character.name
        character_data['user_id'] = character.user_id

    # User Notes

    def get_notes(self, subject_id):
        if subject_id not in self._data['users']:
            return {
                u'result': None,
                u'errors': [
                    u"User ID #{} not found".format(subject_id),
                ],
            }
        notes_data = self._data['notes'].get(subject_id, [])
        notes = [models.Note.from_dict(n) for n in notes_data]
        return {
            u'result': notes,
        }

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
        return {
            u'result': models.Note.from_dict(note_data)
        }
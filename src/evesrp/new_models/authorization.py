import datetime as dt
import enum
import json

import iso8601
import six


class IdEquality(object):

    def __hash__(self):
        return hash(self.id_) ^ hash(self.__class__.__name__)

    def __eq__(self, other):
        # Simplistic, not checking types here.
        return self.id_ == other.id_


class Entity(IdEquality):

    def __init__(self, name, id_):
        self.name = name
        self.id_ = id_

    @classmethod
    def from_dict(cls, entity_dict):
        return cls(entity_dict[u'name'], entity_dict[u'id'])

    def get_permissions(self, store):
        perms = {p.to_tuple() for p in
                 store.get_permissions(entity_id=self.id_)}
        return perms


class User(Entity):

    def get_groups(self, store):
        return store.get_groups(user_id=self.id_)

    def get_permissions(self, store):
        # Get permissions granted to this user in particular first
        permissions = super(User, self).get_permissions(store)
        # ...then for all of the groups we are a member of
        group_permissions = {p for g in self.get_groups(store)
                             for p in g.get_permissions(store)}
        # Set union operator
        return permissions | group_permissions

    def get_notes(self, store):
        return store.get_notes(subject_id=self.id_)


class Group(Entity):

    def get_users(self, store):
        return store.get_users(group_id=self.id_)


class Division(IdEquality):

    def __init__(self, name, id_):
        self.name = name
        self.id_ = id_

    @classmethod
    def from_dict(cls, entity_dict):
        return cls(entity_dict[u'name'], entity_dict[u'id'])


# Enum functional API instead of class-based API
PermissionType = enum.Enum('PermissionType', 'submit review pay admin audit')


def id_from_kwargs(arg_name, kwargs):
    id_name = arg_name + '_id'
    if arg_name not in kwargs and id_name not in kwargs:
        raise ValueError(u"Neither '{}' nor '{}' have been supplied.".format(
            arg_name, id_name))
    elif arg_name in kwargs:
        return kwargs[arg_name].id_
    else:
        return kwargs[id_name]


class Permission(IdEquality):

    def __init__(self, **kwargs):
        self.entity_id = id_from_kwargs('entity', kwargs)
        self.division_id = id_from_kwargs('division', kwargs)
        if 'type_' not in kwargs:
            raise ValueError(u"Permission type required.")
        self.type_ = kwargs['type_']

    @classmethod
    def from_dict(cls, permission_dict):
        type_ = PermissionType[permission_dict[u'type']]
        return cls(type_=type_, entity_id=permission_dict[u'entity_id'],
                   division_id=permission_dict[u'division_id'])

    def to_tuple(self):
        return (self.division_id, self.type_)


class Note(IdEquality):

    def __init__(self, contents, id_, timestamp=None, **kwargs):
        self.subject_id = id_from_kwargs('subject', kwargs)
        self.submitter_id = id_from_kwargs('submitter', kwargs)
        self.id_ = id_
        self.contents = contents
        if timestamp is None:
            self.timestamp = dt.datetime.utcnow()
        else:
            self.timestamp = timestamp

    @classmethod
    def from_dict(cls, note_dict):
        timestamp = note_dict[u'timestamp']
        if isinstance(timestamp, six.string_types):
            timestamp = iso8601.parse_date(timestamp)
        note = cls(contents=note_dict[u'contents'],
                   id_=note_dict[u'id'],
                   timestamp=timestamp,
                   submitter_id=note_dict[u'submitter_id'],
                   subject_id=note_dict[u'subject_id'])
        return note

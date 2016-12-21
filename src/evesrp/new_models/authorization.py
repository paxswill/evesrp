import datetime as dt
import enum
import json

from . import util
from ..util import classproperty


class Entity(util.IdEquality):

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

    def __init__(self, name, id_, admin=False):
        super(User, self).__init__(name, id_)
        self.admin = admin

    @classmethod
    def from_dict(cls, user_dict):
        return cls(user_dict['name'], user_dict['id'],
                   user_dict.get('admin', False))

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

    def add_user(self, store, **kwargs):
        user_id = util.id_from_kwargs('user', kwargs)
        store.associate_user_group(user_id=user_id, group_id=self.id_)

    def remove_user(self, store, **kwargs):
        user_id = util.id_from_kwargs('user', kwargs)
        store.disassociate_user_group(user_id=user_id, group_id=self.id_)


class Division(util.IdEquality):

    def __init__(self, name, id_):
        self.name = name
        self.id_ = id_

    @classmethod
    def from_dict(cls, entity_dict):
        return cls(entity_dict[u'name'], entity_dict[u'id'])

    def add_permission(self, store, type_, **kwargs):
        permission = Permission(division_id=self.id_, type_=type_, **kwargs)
        store.add_permission(permission)
        return permission

    def remove_permission(self, store, **kwargs):
        permission_id = util.id_from_kwargs('permission', kwargs)
        store.remove_permission(permission_id=permission_id)

    def set_name(self, store, new_name):
        self.name = new_name
        store.save_division(self)

    def get_permissions(self, store, type_=None, types=None):
        get_kwargs = {'division_id': self.id_}
        if 'type_' is not None and types is not None:
            raise ValueError(u"Only one of type_ or types is allowed to be "
                             u"specified.")
        if type_ is not None:
            get_kwargs['types'] = (type_,)
        if types is not None:
            get_kwargs['types'] = types
        return store.get_permissions(**get_kwargs)


class PermissionType(enum.Enum):

    submit = u'submit'

    review = u'review'

    pay = u'pay'

    admin = u'admin'

    audit = u'audit'

    @classproperty
    def elevated(cls):
        return frozenset((cls.review, cls.pay, cls.admin, cls.audit))

    @classproperty
    def all(cls):
        return frozenset((cls.submit,
                          cls.review,
                          cls.pay,
                          cls.admin,
                          cls.audit))


class Permission(util.IdEquality):

    def __init__(self, **kwargs):
        self.entity_id = util.id_from_kwargs('entity', kwargs)
        self.division_id = util.id_from_kwargs('division', kwargs)
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


class Note(util.IdEquality):

    def __init__(self, contents, id_, timestamp=None, **kwargs):
        self.subject_id = util.id_from_kwargs('subject', kwargs)
        self.submitter_id = util.id_from_kwargs('submitter', kwargs)
        self.id_ = id_
        self.contents = contents
        if timestamp is None:
            self.timestamp = dt.datetime.utcnow()
        else:
            self.timestamp = timestamp

    @classmethod
    def from_dict(cls, note_dict):
        note = cls(contents=note_dict[u'contents'],
                   id_=note_dict[u'id'],
                   timestamp=util.parse_timestamp(note_dict['timestamp']),
                   submitter_id=note_dict[u'submitter_id'],
                   subject_id=note_dict[u'subject_id'])
        return note

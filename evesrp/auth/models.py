from .. import db
from . import AuthMethod
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.collections import attribute_mapped_collection, collection


users_groups = db.Table('users_groups', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('group_id', db.Integer, db.ForeignKey('group.id')))


perm_users = db.Table('perm_users', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('perm_id', db.Integer, db.ForeignKey('division_perm.id')))


perm_groups = db.Table('perm_groups', db.Model.metadata,
        db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
        db.Column('perm_id', db.Integer, db.ForeignKey('division_perm.id')))


class PermissionMapper(object):
    def __init__(self, data=None):
        if data is None:
            self.data = {'submit': set(), 'review': set(), 'pay': set()}
        else:
            self.data = data

    @collection.appender
    def _append(self, permission):
        permissions = self.data.get(permission.permission)
        permissions.add(permission)

    @collection.remover
    def _remove(self, permission):
        permissions = self.data.get(permission.permission)
        return permissions.remove(permission)

    @collection.iterator
    def __iter__(self):
        yield from self.data.items()

    def __getitem__(self, permission_level):
        return self.data[permission_level]


class User(db.Model):
    """User base class.

    Represents a user, not only those who can submit requests but also
    evaluators and payers. The default implementation does _no_ authentication.
    To provide actual authentication, subclass the User module and implement
    blahdeblahblah.

    TODO: Actually put what to implement.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    user_type = db.Column(db.String(50), nullable=False)
    individual_permissions = db.relationship('DivisionPermission',
            secondary=perm_users,
            collection_class=PermissionMapper,
            back_populates='individuals')

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def __mapper_args__(cls):
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'User':
            args['polymorphic_on'] = cls.user_type
        return args

    @classmethod
    def authmethod(cls):
        return AuthMethod

    def permissions(self, permission):
        divisions = set(self.individual_permissions[permission])
        for group in self.groups:
            divisions.update(group.permissions[permission])
        return divisions

    def has_permission(self, permission):
        return len(self.permissions(permission)) > 0

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Group(db.Model):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    group_type = db.Column(db.String(128), nullable=False)
    users = db.relationship('User', secondary=users_groups, backref='groups',
            collection_class=set)
    permissions = db.relationship('DivisionPermission', secondary=perm_groups,
            collection_class=PermissionMapper,
            back_populates='groups')

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def __mapper_args__(cls):
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'Group':
            args['polymorphic_on'] = cls.group_type
        return args

    @classmethod
    def authmethod(cls):
        return AuthMethod


class DivisionPermission(db.Model):
    __tablename__ = 'division_perm'
    id = db.Column(db.Integer, primary_key=True)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))
    permission = db.Column(db.Enum('submit', 'review', 'pay',
            name='division_permission'), nullable=False)
    individuals = db.relationship('User', secondary=perm_users,
            back_populates='individual_permissions')
    groups = db.relationship('Group', secondary=perm_groups,
            back_populates='permissions')

    @property
    def users(self):
        user_set = set(self.individuals)
        for group in self.groups:
            user_set.union(group.users)

    def __init__(self, division, permission):
        self.permission = permission
        self.division = division

    def add(self, entity):
        if isinstance(entity, User):
            self.individuals.append(entity)
        elif isinstance(entity, Group):
            self.groups.append(entity)
        else:
            # TypeError is correct. It must either be a User, Group or an
            # iterable
            entity_iter = iter(entity)
            for e in entity_iter:
                self.add(e)


class Division(db.Model):
    """A reimbursement division.

    A division has (possible non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    permissions = db.relationship('DivisionPermission', backref='division',
            collection_class=attribute_mapped_collection('permission'))

    def __init__(self, name):
        self.name = name
        for perm in ('submit', 'review', 'pay'):
            DivisionPermission(self, perm)

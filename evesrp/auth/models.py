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
        permissions = self.data.get(permission.permissions)
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
    division_admin = db.Column(db.Boolean, nullable=False, default=False)
    full_admin = db.Column(db.Boolean, nullable=False, default=False)
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
        if cls.__name == 'User':
            args['polymorphic_on'] = user_type
        return args

    @declared_attr
    def id(cls):
        col = db.Column(db.Integer, primary_key=True)
        if cls.__name__ != 'User':
            col.append_foreign_key(db.ForeignKey('user.id'))
        return col

    @classmethod
    def authmethod(cls):
        return AuthMethod

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)


class Group(db.Model):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    # TODO: Consider if you should allow groups from different AuthMethods to
    # be 'merged'
    users = db.relationship('User', secondary=users_groups, backref='groups',
            collection_class=set)
    permissions = db.relationship('DivisionPermission', secondary=perm_groups,
            collection_class=PermissionMapper,
            back_populates='groups')


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
        for group in groups:
            user_set.union(group.users)


class Division(db.Model):
    """A reimbursement division.

    A division has (possible non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    permissions = db.relationship('DivisionPermission', backref='division'
            collection_class=attribute_mapped_collection('permission'))

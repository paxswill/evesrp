from .. import db
from . import AuthMethod
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection, collection
from ..models import Action, Modifier, Request, AutoID


users_groups = db.Table('users_groups', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('group_id', db.Integer, db.ForeignKey('group.id')))


perm_users = db.Table('perm_users', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('perm_id', db.Integer, db.ForeignKey('division_perm.id')))


perm_groups = db.Table('perm_groups', db.Model.metadata,
        db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
        db.Column('perm_id', db.Integer, db.ForeignKey('division_perm.id')))


class User(db.Model, AutoID):
    """User base class.

    Represents a user, not only those who can submit requests but also
    evaluators and payers. The default implementation does _no_ authentication.
    To provide actual authentication, subclass the User module and implement
    blahdeblahblah.

    TODO: Actually put what to implement.
    """
    name = db.Column(db.String(100), nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    user_type = db.Column(db.String(50), nullable=False)
    individual_permissions = db.relationship('DivisionPermission',
            secondary=perm_users,
            collection_class=attribute_mapped_collection('permission'),
            back_populates='individuals')
    requests = db.relationship(Request, back_populates='submitter')
    individual_divisions = association_proxy('individual_permissions',
            'division')
    actions = db.relationship(Action, back_populates='user')

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

    @property
    def permissions(self):
        class _PermProxy(object):
            def __init__(self, user):
                self.user = user

            def __getitem__(self, key):
                perms = set()
                try:
                    perms = self.user.individual_permissions[key]
                except TypeError:
                    perms.add(self.user.individual_permissions[key])
                except KeyError:
                    pass
                for group in self.user.groups:
                    try:
                        perms.update(group.permissions[key])
                    except TypeError:
                        perms.add(group.permissions[key])
                    except KeyError:
                        pass
                return perms
        return _PermProxy(self)

    @property
    def divisions(self):
        class _DivProxy(object):
            def __init__(self, user):
                self.user = user

            def __getitem__(self, key):
                divs = set()
                try:
                    divs.update(self.user.individual_divisions[key])
                except TypeError:
                    divs.add(self.user.individual_divisions[key])
                except KeyError:
                    pass
                for group in self.user.groups:
                    try:
                        divs.update(group.divisions[key])
                    except TypeError:
                        divs.add(group.divisions[key])
                    except KeyError:
                        pass
                return divs
        return _DivProxy(self)

    def has_permission(self, permission):
        return len(self.divisions[permission]) > 0

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Group(db.Model, AutoID):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """
    name = db.Column(db.String(128), nullable=False, index=True)
    group_type = db.Column(db.String(128), nullable=False)
    users = db.relationship(User, secondary=users_groups, backref='groups',
            collection_class=set)
    permissions = db.relationship('DivisionPermission', secondary=perm_groups,
            collection_class=attribute_mapped_collection('permission'),
            back_populates='groups')
    divisions = association_proxy('permissions', 'division')

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


class DivisionPermission(db.Model, AutoID):
    __tablename__ = 'division_perm'
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))
    permission = db.Column(db.Enum('submit', 'review', 'pay',
            name='division_permission'), nullable=False)
    individuals = db.relationship(User, secondary=perm_users,
            back_populates='individual_permissions')
    groups = db.relationship(Group, secondary=perm_groups,
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
            for e in entity:
                self.add(e)

    def remove(self, entity):
        if isinstance(entity, User):
            self.individuals.remove(entity)
        elif isinstance(entity, Group):
            self.groups.remove(entity)
        else:
            for e in entity:
                self.remove(e)


class Division(db.Model, AutoID):
    """A reimbursement division.

    A division has (possible non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'division'
    name = db.Column(db.String(128), nullable=False)
    permissions = db.relationship(DivisionPermission, backref='division',
            collection_class=attribute_mapped_collection('permission'))
    requests = db.relationship(Request, back_populates='division')

    def __init__(self, name):
        self.name = name
        for perm in ('submit', 'review', 'pay'):
            DivisionPermission(self, perm)

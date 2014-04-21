from .. import db
from . import AuthMethod
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection, collection
from ..models import Action, Modifier, Request, AutoID, Timestamped


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

    Represents users who can submit, review and/or pay out requests. It also
    supplies a number of convenience methods for subclasses.
    """
    #: The name of the user. Usually a nickname.
    name = db.Column(db.String(100), nullable=False)

    #: If the user is an administrator. This allows the user to create and
    #: administer divisions.
    admin = db.Column(db.Boolean, nullable=False, default=False)

    #: Map of permission objects granted specifically to this user. Keys are
    #: one of the permission values.
    individual_permissions = db.relationship('DivisionPermission',
            secondary=perm_users,
            collection_class=attribute_mapped_collection('permission'),
            back_populates='individuals')

    #: Map of :py:class:`Division` s this user has been specifically granted
    #: permissions in. Keys are one of the permissions values.
    individual_divisions = association_proxy('individual_permissions',
            'division')

    #: :py:class:`~.Request` s this user has submitted.
    requests = db.relationship(Request, back_populates='submitter')

    #: :py:class:`~.Action` s this user has performed on requests.
    actions = db.relationship(Action, back_populates='user')

    #: :py:class:`~.Pilot` s associated with this user.
    pilots = db.relationship('Pilot', back_populates='user',
            collection_class=set)
    notes = db.relationship('Note', back_populates='user',
            order_by='desc(Note.timestamp)', foreign_keys='Note.user_id')
    notes_made = db.relationship('Note', back_populates='noter',
            order_by='desc(Note.timestamp)', foreign_keys='Note.noter_id')

    #: Polymorphic discriminator column.
    user_type = db.Column(db.String(50), nullable=False)

    @declared_attr
    def __tablename__(cls):
        """SQLAlchemy late-binding attribute to set the table name.

        Implemented this way so subclasses do not need to specify a table name
        themselves.
        """
        return cls.__name__.lower()

    @declared_attr
    def __mapper_args__(cls):
        """SQLAlchemy late-binding attribute to set mapper arguments.

        Obviates subclasses from having to specify polymorphic identities.
        """
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'User':
            args['polymorphic_on'] = cls.user_type
        return args

    @classmethod
    def authmethod(cls):
        """:rtype: class
        :returns: The :py:class:`AuthMethod` for this user class.
        """
        return AuthMethod

    @property
    def permissions(self):
        """Map of all permissions a user has been granted, including those
        granted through groups. Keys are permissions values, like those given
        to :py:attr:`individual_permissions`.
        """
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
        """Map of all divisions a user has been granted permissions in,
        including those granted through groups."""
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

    def __init__(self, name, **kwargs):
        self.name
        super(User, self).__init__(**kwargs)

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}')".format(x=self)

    def __str__(self):
        return "{x.name}".format(x=self)

    def has_permission(self, permission):
        """Check if the user can access any division with the given permission
        level.

        :param str permission: The permission level to check.
        :return: If it can access a division with that permission.
        :rtype: bool
        """
        return len(self.divisions[permission]) > 0

    def is_authenticated(self):
        """Part of the interface for Flask-Login."""
        return True

    def is_active(self):
        """Part of the interface for Flask-Login."""
        return True

    def is_anonymous(self):
        """Part of the interface for Flask-Login."""
        return False

    def get_id(self):
        """Part of the interface for Flask-Login."""
        return str(self.id)


class Note(db.Model, AutoID, Timestamped):
    __tablename__ = 'note'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, back_populates='notes',
            foreign_keys=[user_id])
    content = db.Column(db.Text, nullable=False)
    noter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    noter = db.relationship(User, back_populates='notes_made',
            foreign_keys=[noter_id])



class Pilot(db.Model, AutoID):
    """Represents an in-game character."""
    __tablename__ = 'pilot'

    #: The name of the character
    name = db.Column(db.String(150), nullable=False)

    #: The id of the User this character belongs to.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #: The User this character belongs to.
    user = db.relationship(User, back_populates='pilots')

    #: The Requests filed with lossmails from this character.
    requests = db.relationship(Request, back_populates='pilot',
            collection_class=list, order_by=Request.timestamp.desc())

    def __init__(self, user, name, id_):
        """Create a new Pilot instance.

        :param user: The user this character belpongs to.
        :type user: :py:class:`~.User`
        :param str name: The name of this character.
        :param int id_: The CCP-given characterID number.
        """
        self.user = user
        self.name = name
        self.id = id_

    def __repr__(self):
        return "{x.__class__.__name__({x.user}, '{x.name}', {x.id})".format(
                x=self)


class Group(db.Model, AutoID):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """

    #: The name of this group.
    name = db.Column(db.String(128), nullable=False, index=True)

    #: Polymorphic discriminator column
    group_type = db.Column(db.String(128), nullable=False)

    #: :py:class:`User` s that belong to this group.
    users = db.relationship(User, secondary=users_groups, backref='groups',
            collection_class=set)

    #: Permission association objects.
    # For internal use.
    permissions = db.relationship('DivisionPermission', secondary=perm_groups,
            collection_class=attribute_mapped_collection('permission'),
            back_populates='groups')

    #: :py:class:`Division` s this group has been granted permissions to.
    divisions = association_proxy('permissions', 'division')

    @declared_attr
    def __tablename__(cls):
        """Convenience method easing subclassing."""
        return cls.__name__.lower()

    @declared_attr
    def __mapper_args__(cls):
        """Automatic mapper arguements for easy subclasing."""
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'Group':
            args['polymorphic_on'] = cls.group_type
        return args

    @classmethod
    def authmethod(cls):
        """:returns: The AuthMethod subclass for this group class.
        :rtype: :py:func:`type`
        """
        return AuthMethod

    def __init__(self, name, **kwargs):
        self.name = name
        super(Group, self).__init__(**kwargs)

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}')".format(x=self)

    def __str__(self):
        return "{x.name}".format(x=self)


class DivisionPermission(db.Model, AutoID):
    __tablename__ = 'division_perm'
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))
    permission = db.Column(db.Enum('submit', 'review', 'pay',
            name='division_permission'), nullable=False)
    individuals = db.relationship(User, secondary=perm_users,
            back_populates='individual_permissions', collection_class=set)
    groups = db.relationship(Group, secondary=perm_groups,
            back_populates='permissions', collection_class=set)

    @property
    def users(self):
        """A :py:class:`set` of all users granted this permission."""
        user_set = set(self.individuals)
        for group in self.groups:
            user_set.union(group.users)

    def __init__(self, division, permission):
        self.permission = permission
        self.division = division

    def __repr__(self):
        return "{x.__class__.__name__}({x.division}, '{x.permission}')".format(
                x=self)

    def add(self, entity):
        """Add a User, Group, or an iterable of them to this permission.

        :param entity: The user, group, or iterable to add to this permission.
        :type entity: A :py:class:`User`, :py:class:`Group` or an iterable of
        those types (a mixed iterable of both types is allowed).
        """
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
        """Remove a User, Group or iterable from this permission.

        :param entity: The user(s) and/or group(s) to remove.
        :type entity: A :py:class:`User`, :py:class:`Group` or an iterable of
        some combination of those types.
        """
        if isinstance(entity, User):
            self.individuals.remove(entity)
        elif isinstance(entity, Group):
            self.groups.remove(entity)
        else:
            for e in entity:
                self.remove(e)


class Division(db.Model, AutoID):
    """A reimbursement division.

    A division has (possibly non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'division'

    #: The name of this division.
    name = db.Column(db.String(128), nullable=False)

    #: The permissions objects for this division, mapped via their permission
    #: names.
    permissions = db.relationship(DivisionPermission, backref='division',
            collection_class=attribute_mapped_collection('permission'))

    #: :py:class:`Request` s filed under this division.
    requests = db.relationship(Request, back_populates='division')

    def __init__(self, name):
        self.name = name
        for perm in ('submit', 'review', 'pay'):
            DivisionPermission(self, perm)

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}')".format(x=self)

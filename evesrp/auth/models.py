from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.collections import attribute_mapped_collection, collection

from .. import db
from . import AuthMethod
from ..models import Action, Modifier, Request, AutoID, Timestamped


users_groups = db.Table('users_groups', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('group_id', db.Integer, db.ForeignKey('group.id')))


class Entity(db.Model, AutoID):
    """Private class for shared functionality between :py:class:`User` and
    :py:class:`Group`.

    This class defines a number of helper methods used indirectly by User and
    Group subclasses such as automatically defining the table name and mapper
    arguments.

    You should `not` inherit fomr this class directly, and should instead
    inherit from either :py:class:`User` or :py:class:`Group`.
    """

    #: The name of the entity. Usually a nickname.
    name = db.Column(db.String(100), nullable=False)

    #: Polymorphic discriminator column.
    type_ = db.Column(db.String(50))

    #: :py:class:`Permission`\s associated specifically with this entity.
    entity_permissions = db.relationship('Permission', collection_class=set,
            back_populates='entity', lazy='dynamic')

    #: The name of the :py:class:`AuthMethod` for this entity.
    authmethod = db.Column(db.String(50), nullable=False)

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
        if cls.__name__ == 'Entity':
            args['polymorphic_on'] = cls.type_
        return args

    def __init__(self, name, authmethod, **kwargs):
        self.name = name
        self.authmethod = authmethod
        super(Entity, self).__init__(**kwargs)

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}')".format(x=self)

    def __str__(self):
        return "{x.name}".format(x=self)

    def has_permission(self, permissions, division=None):
        """Returns if this entity has been granted a permission in a division.

        If ``division`` is ``None``, this method checks if this group has the
        given permission in `any` division.

        :param permissions: The series of permissions to check
        :type permissions: iterable
        :param division: The division to check. May be ``None``.
        :type division: :py:class:`Division`
        :rtype bool:
        """
        if permissions in ('submit', 'review', 'pay'):
            permissions = (permissions,)
        perms = self.permissions.filter(Permission.permission.in_(permissions))
        if division is not None:
            perms = perms.filter_by(division=division)
        return db.session.query(perms.exists()).all()[0][0]


class User(Entity):
    """User base class.

    Represents users who can submit, review and/or pay out requests. It also
    supplies a number of convenience methods for subclasses.
    """
    id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)

    #: If the user is an administrator. This allows the user to create and
    #: administer divisions.
    admin = db.Column(db.Boolean, nullable=False, default=False)

    #: :py:class:`~.Request`\s this user has submitted.
    requests = db.relationship(Request, back_populates='submitter')

    #: :py:class:`~.Action`\s this user has performed on requests.
    actions = db.relationship(Action, back_populates='user')

    #: :py:class:`~.Pilot`\s associated with this user.
    pilots = db.relationship('Pilot', back_populates='user',
            collection_class=set)

    #: :py:class:`Group`\s this user is a member of
    groups = db.relationship('Group', secondary=users_groups,
            back_populates='users', collection_class=set)

    notes = db.relationship('Note', back_populates='user',
            order_by='desc(Note.timestamp)', foreign_keys='Note.user_id')

    notes_made = db.relationship('Note', back_populates='noter',
            order_by='desc(Note.timestamp)', foreign_keys='Note.noter_id')

    @hybrid_property
    def permissions(self):
        """All :py:class:`Permission` objects associated with this user."""
        groups = db.session.query(users_groups.c.group_id.label('group_id'))\
                .filter(users_groups.c.user_id==self.id).subquery()
        group_perms = db.session.query(Permission)\
                .join(groups, groups.c.group_id==Permission.entity_id)
        user_perms = db.session.query(Permission)\
                .join(User)\
                .filter(User.id==self.id)
        perms = user_perms.union(group_perms)
        return perms

    @permissions.expression
    def permissions(cls):
        groups = db.select([users_groups.c.group_id])\
                .where(users_groups.c.user_id==cls.id).alias()
        group_permissions = db.select([Permission])\
                .where(Permission.entity_id.in_(groups)).alias()
        user_permissions = db.select([Permission])\
                .where(Permission.entity_id==cls.id)
        return user_permissions.union(group_permissions)

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

    def __init__(self, user, noter, note):
        self.user = user
        self.noter = noter
        self.content = note


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
        return "{x.__class__.__name__}({x.user}, '{x.name}', {x.id})".format(
                x=self)


class Group(Entity):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """

    id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)

    #: :py:class:`User` s that belong to this group.
    users = db.relationship(User, secondary=users_groups,
            back_populates='groups', collection_class=set)

    #: Synonym for :py:attr:`entity_permissions`
    permissions = db.synonym('entity_permissions')


class Permission(db.Model, AutoID):
    __tablename__ = 'permission'
    __table_args__ = (
        db.UniqueConstraint('division_id', 'entity_id', 'permission'),
    )

    division_id = db.Column(db.Integer, db.ForeignKey('division.id'),
            nullable=False)

    #: The division this permission is granting access to
    division = db.relationship('Division',
            back_populates='division_permissions')

    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'),
            nullable=False)

    #: The :py:class:`Entity` being granted access
    entity = db.relationship(Entity, back_populates='entity_permissions')

    #: The permission being granted.
    permission = db.Column(db.Enum('submit', 'review', 'pay',
            name='division_permission'), nullable=False)

    def __init__(self, division, permission, entity):
        """Create a Permission object granting an entity access to a division.
        """
        self.division = division
        self.entity = entity
        self.permission = permission

    def __repr__(self):
        return ("{x.__class__.__name__}('{x.permission}', {x.entity}, "
               "{x.division})").format(x=self)


class Division(db.Model, AutoID):
    """A reimbursement division.

    A division has (possibly non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'division'

    #: The name of this division.
    name = db.Column(db.String(128), nullable=False)

    #: All :py:class:`Permission`\s associated with this division.
    division_permissions = db.relationship(Permission, collection_class=set,
            back_populates='division')

    #: :py:class:`Request` s filed under this division.
    requests = db.relationship(Request, back_populates='division')

    ship_transformer = db.Column(db.PickleType, nullable=True, default=None)

    pilot_transformer = db.Column(db.PickleType, nullable=True, default=None)

    @property
    def permissions(self):
        """The permissions objects for this division, mapped via their
        permission names.
        """
        class _PermProxy(object):
            def __init__(self, perms):
                self.perms = perms
            def __getitem__(self, key):
                return set(filter(lambda x: x.permission == key, self.perms))
        return _PermProxy(self.division_permissions)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}')".format(x=self)

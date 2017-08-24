# -*- coding: utf-8 -*-
import sqlalchemy as sqla
from sqlalchemy_utils import UUIDType, JSONType

from evesrp import new_models as models


metadata = sqla.MetaData(
    naming_convention = {
        'fk': ('fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'
               '_%(referred_column_0_name)s'),
        'pk': 'pk_%(table_name)s',
        'ix': 'ix_%(table_name)s_%(column_0_name)s',
        'ck': 'ck_%(table_name)s_%(constraint_name)s',
        'uq': 'uq_%(table_name)s_%(column_0_name)s',
    }
)


# TODO Add event listener to change 'utf8' collation on mysql to 'utf8mb4'.
# This is because MySQL's 'utf8' collation only supports 1-3 byte characters 🤔


authn_entity = sqla.Table(
    'authn_entity',
    metadata,
    sqla.Column('type', sqla.Enum('user', 'group', native_enum=True,
                                  name='authn_entity_type'),
                primary_key=True, nullable=False),
    sqla.Column('provider_uuid', UUIDType(binary=True, native=True),
                primary_key=True, nullable=False),
    sqla.Column('provider_key', sqla.String(255),
                primary_key=True, nullable=False),
    sqla.Column('entity_id', sqla.ForeignKey('entity.id'), primary_key=True,
                nullable=False),
    sqla.Column('data', JSONType, nullable=True)
)


entity = sqla.Table(
    'entity',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('type', sqla.String(20), nullable=False),
    sqla.Column('name', sqla.Unicode(255), nullable=False)
)


user = sqla.Table(
    'user',
    metadata,
    sqla.Column('id', sqla.ForeignKey(entity.c.id), primary_key=True,
                nullable=False),
    sqla.Column('admin', sqla.Boolean(name='user_admin'), nullable=False,
                                      default=False)
)


user_group = sqla.Table(
    'user_group',
    metadata,
    # TODO Add a check constraint that user_id has a type user, and group_id to
    # a type group.
    sqla.Column('user_id', sqla.ForeignKey(user.c.id), primary_key=True,
                nullable=False),
    sqla.Column('group_id', sqla.ForeignKey(entity.c.id), primary_key=True,
                nullable=False),
)


division = sqla.Table(
    'division',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    # Because there will be someone who wants their division to be named the
    # thinking emoji.
    sqla.Column('name', sqla.Unicode(255), nullable=False)
)


permission = sqla.Table(
    'permission',
    metadata,
    sqla.Column('entity_id', sqla.ForeignKey(entity.c.id), primary_key=True,
                nullable=False),
    sqla.Column('division_id', sqla.ForeignKey(division.c.id),
                primary_key=True, nullable=False),
    sqla.Column('type', sqla.Enum(models.PermissionType, native_enum=True,
                                  name='permission_type'),
                primary_key=True, nullable=False),
    sqla.Index('ix_permission_division_id', 'division_id')
)


note = sqla.Table(
    'note',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('subject_id', sqla.ForeignKey(user.c.id), nullable=False),
    sqla.Column('submitter_id', sqla.ForeignKey(user.c.id), nullable=False),
    sqla.Column('content', sqla.UnicodeText(), nullable=False),
    sqla.Column('timestamp', sqla.TIMESTAMP(timezone=True), nullable=False,
                server_default=sqla.func.now())
)


ccp_name = sqla.Table(
    'ccp_name',
    metadata,
    sqla.Column('type', sqla.String(50), primary_key=True,
                nullable=False),
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    # ccp_name.name is also known as the english name of the thing
    sqla.Column('name', sqla.Unicode(255), nullable=False),
    # TODO Maybe add additional columns for the other languages officially
    # supported by CCP (DE, FR, JA, ZH, and RU)
    sqla.CheckConstraint(
        sqla.type_coerce('type', sqla.String).in_(
            ['character', 'corporation', 'alliance',
             'system', 'constellation', 'region',
             'type']
        ),
        name='ccp_name_type'
    ),
    sqla.UniqueConstraint('id')
)


character = sqla.Table(
    'character',
    metadata,
    # TODO Investigate if we can ad a check constraint so that ccp_name.id has
    # a ccp_name.type == 'character'
    sqla.Column('ccp_id', sqla.ForeignKey(ccp_name.c.id), primary_key=True,
                nullable=False),
    # Characters do not necesarily belong to a specific user (like if a
    # character is biomassed, or transferred to another account).
    sqla.Column('user_id', sqla.ForeignKey(user.c.id), nullable=True,
                index=True),
)


killmail = sqla.Table(
    'killmail',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('user_id', sqla.ForeignKey(user.c.id), nullable=False,
                index=True),
    # TODO add a bevy of check constraints
    sqla.Column('character_id', sqla.ForeignKey(character.c.ccp_id),
                nullable=False, index=True),
    sqla.Column('corporation_id', sqla.ForeignKey(ccp_name.c.id),
                nullable=False),
    # Alliance is explicitly nullable; not all corps are in alliances
    sqla.Column('alliance_id', sqla.ForeignKey(ccp_name.c.id), nullable=True),
    sqla.Column('system_id', sqla.ForeignKey(ccp_name.c.id), nullable=False),
    sqla.Column('constellation_id', sqla.ForeignKey(ccp_name.c.id),
                nullable=False),
    sqla.Column('region_id', sqla.ForeignKey(ccp_name.c.id), nullable=False),
    sqla.Column('type_id', sqla.ForeignKey(ccp_name.c.id), nullable=False),
    # No default given as this value should be taken from the killmail data
    # from CCP
    sqla.Column('timestamp', sqla.TIMESTAMP(timezone=True), nullable=False),
    sqla.Column('url', sqla.String(255), nullable=False)
)


request = sqla.Table(
    'request',
    metadata,
    # NOTE The primary key is /not/ request.id, but a composite of
    # request.killmail_id and request.division_id
    sqla.Column('id', sqla.Integer, primary_key=False, nullable=False,
                autoincrement=True, index=True),
    sqla.Column('killmail_id', sqla.ForeignKey(killmail.c.id),
                primary_key=True, nullable=False),
    sqla.Column('division_id', sqla.ForeignKey(division.c.id),
                primary_key=True, nullable=False),
    # TODO possible improvement for later down the line: move details to a
    # separate table, so changing details just adds a new entry, and the
    # current details are just the latest entry in there. Not sure it'd be a
    # useful improvement though
    sqla.Column('details', sqla.UnicodeText(), nullable=False,
                server_default=u''),
    sqla.Column('timestamp', sqla.TIMESTAMP(timezone=True), nullable=False,
                server_default=sqla.func.now()),
    # TODO: Subclass sqla.Enum to persist the /values/ of the enum to the DB,
    # as we're using that to sort statuses.
    # TODO: Investigate adding checking at the DB level that the status is
    # changing appropriately.
    sqla.Column('status', sqla.Enum(models.ActionType, native_enum=False,
                                    name='request_status'),
                nullable=False, default=models.ActionType.evaluating),
    sqla.Column('base_payout', sqla.Numeric(precision=15, scale=2),
                nullable=False, server_default='0'),
    # TODO add a 'something' (trigger? function?) to automatically update the
    # payout based on base_payout and modifiers
    sqla.Column('payout', sqla.Numeric(precision=15, scale=2),
                nullable=False, server_default='0'),
    # TODO: Add FTS index for details column
    sqla.UniqueConstraint('id')
)


action = sqla.Table(
    'action',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('request_id', sqla.ForeignKey(request.c.id), nullable=False,
                index=True),
    sqla.Column('user_id', sqla.ForeignKey(user.c.id), nullable=False),
    # Possible linking of this with request.status.type checking
    sqla.Column('type', sqla.Enum(models.ActionType, native_enum=False,
                                  name='action_type'),
                nullable=False, default=models.ActionType.evaluating),
    sqla.Column('details', sqla.UnicodeText(), nullable=False,
                server_default=u''),
    sqla.Column('timestamp', sqla.TIMESTAMP(timezone=True), nullable=False,
                server_default=sqla.func.now())
)


modifier = sqla.Table(
    'modifier',
    metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('type', sqla.Enum(models.ModifierType, native_enum=True,
                                  name='modifier_type'),
                nullable=False),
    sqla.Column('user_id', sqla.ForeignKey(user.c.id), nullable=False),
    sqla.Column('request_id', sqla.ForeignKey(request.c.id), nullable=False),
    sqla.Column('note', sqla.UnicodeText(), nullable=False,
                server_default=u''),
    sqla.Column('value', sqla.Numeric(precision=15, scale=5), nullable=False),
    sqla.Column('timestamp', sqla.TIMESTAMP(timezone=True), nullable=False,
                server_default=sqla.func.now()),
    # TODO: Maybe add a virtual boolean column modifier.void based on if these
    # two are null or not
    # TODO Add a check constraint that these are both null or both non-null
    sqla.Column('void_user_id', sqla.ForeignKey(user.c.id), nullable=True),
    sqla.Column('void_timestamp', sqla.TIMESTAMP(timezone=True),
                nullable=True),
    # TODO: possibly add index on only active (aka non-voided) modifiers
)


__all__ = ['metadata', 'authn_entity', 'entity', 'user', 'user_group',
           'division', 'permission', 'note', 'ccp_name', 'character',
           'killmail', 'request', 'action', 'modifier']

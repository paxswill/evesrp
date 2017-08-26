from __future__ import absolute_import

import collections
import itertools

import six
import sqlalchemy as sqla
import sqlalchemy.exc

from .. import BaseStore, CachingCcpStore, errors
from evesrp import new_models as models
from evesrp import search_filter
from . import ddl


class SqlStore(CachingCcpStore, BaseStore):

    def __init__(self, **kwargs):
        if 'connection' in kwargs:
            self.connection = kwargs.pop('connection')
        else:
            engine = kwargs.pop('engine')
            self.connection = engine.connect()

    @staticmethod
    def create(engine):
        """Create the database struture."""
        ddl.metadata.create_all(engine)

    @staticmethod
    def destroy(engine):
        """Drop all database tables."""
        ddl.metadata.drop_all(engine)

    @staticmethod
    def _check_update_result(kind, identifier, result, expected=1):
        if result.supports_sane_rowcount() and result.rowcount != expected:
            if result.rowcount == 0:
                raise errors.NotFoundError(kind, identifier)
            else:
                raise errors.StorageError(kind, identifier)

    # Authentication

    _authn_select = sqla.select(
        [
            ddl.authn_entity.c.provider_uuid,
            ddl.authn_entity.c.provider_key,
            ddl.authn_entity.c.entity_id,
            ddl.authn_entity.c.data,
        ]
    ).where(
        sqla.and_(
            ddl.authn_entity.c.provider_uuid == sqla.bindparam('uuid'),
            ddl.authn_entity.c.provider_key == sqla.bindparam('key'),
            ddl.authn_entity.c.type == sqla.bindparam('type_')
        )
    )

    def _get_authn(self, type_, provider_uuid, provider_key):
        result = self.connection.execute(self._authn_select,
                                         uuid=provider_uuid,
                                         key=provider_key,
                                         type_=type_)
        row = result.first()
        if row is None:
            raise errors.NotFoundError(
                'Authenticated{}'.format(type_.capitalize()),
                '({}, {})'.format(provider_uuid, provider_key)
            )
        else:
            entity_args = {
                'provider_uuid': row['provider_uuid'],
                'provider_key': row['provider_key'],
                'extra_data': row['data']
            }
            if type_ == 'user':
                Entity = models.AuthenticatedUser
                entity_args['user_id'] = row['entity_id']
            elif type_ == 'group':
                Entity = models.AuthenticatedGroup
                entity_args['group_id'] = row['entity_id']
            return Entity(**entity_args)

    _authn_insert = ddl.authn_entity.insert()

    def _add_authn(self, type_, entity_id, provider_uuid, provider_key,
                   extra_data=None, *kwargs):
        if extra_data is None:
            extra_data = {}
        extra_data.update(kwargs)
        try:
            result = self.connection.execute(self._authn_insert,
                                             type=type_,
                                             entity_id=entity_id,
                                             provider_key=provider_key,
                                             provider_uuid=provider_uuid,
                                             data=extra_data)
        except sqla.exc.IntegrityError as integrity_exc:
            # The only constraint (besides a possible check constraint on DBs
            # that don't have native enums) is a foreign key constraint on
            # entity_id
            not_found_exc = errors.NotFoundError(
                'Authenticated{}'.format(type_.captialize()),
                entity_id
            )
            six.raise_from(not_found_exc, integrity_exc)
        else:
            result.close()
            authn_entity_args = {
                'provider_uuid': provider_uuid,
                'provider_key': provider_key,
                'extra_data': extra_data,
            }
            if type_ == 'user':
                Entity = models.AuthenticatedUser
                authn_entity_args['user_id'] = entity_id
            elif type_ == 'group':
                Entity = models.AuthenticatedGroup
                authn_entity_args['group_id'] = entity_id
            return Entity(**authn_entity_args)

    _authn_update = ddl.authn_entity.update().where(
        sqla.and_(
            ddl.authn_entity.c.provider_uuid == sqla.bindparam('uuid'),
            ddl.authn_entity.c.provider_key == sqla.bindparam('key'),
            ddl.authn_entity.c.type == sqla.bindparam('type_')
        )
    )

    def _save_authn(self, type_, authn_entity):
        entity_id = getattr(authn_entity, type_ + '_id')
        result = self.connection.execute(self._authn_update,
                                         uuid=authn_entity.provider_uuid,
                                         key=authn_entity.provider_key,
                                         entity_id=entity_id,
                                         data=authn_entity.extra_data,
                                         type_=type_)
        result.close()
        self._check_update_result(type_, entity_id, result)

    def get_authn_user(self, provider_uuid, provider_key):
        return self._get_authn('user', provider_uuid, provider_key)

    def add_authn_user(self, user_id, provider_uuid, provider_key,
                       extra_data=None, **kwargs):
        return self._add_authn('user', user_id, provider_uuid, provider_key,
                               extra_data=extra_data, **kwargs)

    def save_authn_user(self, authn_user):
        self._save_authn('user', authn_user)

    def get_authn_group(self, provider_uuid, provider_key):
        return self._get_authn('group', provider_uuid, provider_key)

    def add_authn_group(self, group_id, provider_uuid, provider_key,
                        extra_data=None, **kwargs):
        return self._add_authn('group', group_id, provider_uuid, provider_key,
                               extra_data=extra_data, **kwargs)

    def save_authn_group(self, authn_group):
        self._save_authn('group', authn_group)

    # Divisions

    _division_select = sqla.select([
        ddl.division.c.id,
        ddl.division.c.name,
    ]).where(
        ddl.division.c.id == sqla.bindparam('division_id')
    )

    def get_division(self, division_id):
        result = self.connection.execute(
            self._division_select,
            division_id=division_id
        )
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Division', division_id)
        return models.Division(
            name=row['name'],
            id_=row['id']
        )

    _divisions_select = sqla.select([
        ddl.division.c.id,
        ddl.division.c.name,
    ])

    def get_divisions(self, division_ids=None):
        select_stmt = self._divisions_select
        if division_ids is not None:
            select_stmt = select_stmt.where(
                ddl.division.c.id.in_(division_ids)
            )
        result = self.connection.execute(select_stmt)
        rows = result.fetchall()
        result.close()
        return [models.Division(row['name'], row['id']) for row in rows]

    _division_insert = ddl.division.insert()

    def add_division(self, name):
        result = self.connection.execute(self._division_insert,
                                         name=name)
        new_id = result.inserted_primary_key[0]
        result.close()
        return self.get_division(new_id)

    _division_update = ddl.division.update().where(
        ddl.division.c.id == sqla.bindparam('division_id')
    )

    def save_division(self, division):
        result = self.connection.execute(self._division_update,
                                         division_id=division.id_,
                                         name=division.name)
        result.close()
        self._check_update_result('Division', division.id_, result)

    # Permissions

    def get_permissions(self, **kwargs):
        # Start with selecting all, adding where clauses as given by the
        # arguments
        stmt = ddl.permission.select()
        conditions = []
        for key in ('entity_id', 'division_id', 'type_'):
            value = kwargs.get(key)
            if key == 'type_':
                column = ddl.permission.c.type
            else:
                column = getattr(ddl.permission.c, key)
            if isinstance(value, (int, models.PermissionType)):
                conditions.append(column == value)
            elif isinstance(value, collections.Iterable):
                conditions.append(column.in_(value))
        result = self.connection.execute(stmt.where(sqla.and_(*conditions)))
        rows = result.fetchall()
        result.close()
        return [models.Permission(row['division_id'], row['entity_id'],
                                  row['type'])
                for row in rows]

    _permission_insert = ddl.permission.insert()

    def add_permission(self, division_id, entity_id, type_):
        try:
            result = self.connection.execute(
                self._permission_insert,
                division_id=division_id,
                entity_id=entity_id,
                type=type_
            )
        except sqla.exc.IntegrityError as exc:
            error_message = str(exc.orig)
            if 'entity_id' in error_message:
                new_exc = errors.NotFoundError('Entity', entity_id)
            elif 'division_id' in error_message:
                new_exc = errors.NotFoundError('Division', division_id)
            else:
                raise
            six.raise_from(new_exc, exc)
        return models.Permission(division_id, entity_id, type_)

    _permission_delete = ddl.permission.delete().where(
        sqla.and_(
            ddl.permission.c.entity_id == sqla.bindparam('entity_id'),
            ddl.permission.c.division_id == sqla.bindparam('division_id'),
            ddl.permission.c.type == sqla.bindparam('type_'),
        )
    )

    def remove_permission(self, *args, **kwargs):
        if len(args) == 1 or 'permission' in kwargs:
            try:
                permission = kwargs['permission']
            except KeyError:
                permission = args[0]
            delete_args = {
                'division_id': permission.division_id,
                'entity_id': permission.entity_id,
                'type_': permission.type_,
            }
        elif len(args) == 3:
            delete_args = {
                'division_id': args[0],
                'entity_id': args[1],
                'type_': args[2],
            }
        else:
            delete_args = kwargs
        result = self.connection.execute(self._permission_delete,
                                         **delete_args)
        # Not checking result, as we don't raise errors if nothing was deleted

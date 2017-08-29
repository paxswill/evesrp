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
        super(SqlStore, self).__init__(**kwargs)

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
            if 'fk_permission_entity_id_entity_id' in error_message:
                new_exc = errors.NotFoundError('Entity', entity_id)
            elif 'fk_permission_division_id_division_id' in error_message:
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

    # Users and Groups

    _user_select = sqla.select([
        ddl.entity.c.id,
        ddl.entity.c.name,
        ddl.user.c.admin,
    ]).select_from(
        ddl.entity.join(ddl.user)
    ).where(
        ddl.entity.c.id == sqla.bindparam('user_id')
    )

    def get_user(self, user_id):
        result = self.connection.execute(self._user_select, user_id=user_id)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('User', user_id)
        return models.User(row['name'], row['id'], row['admin'])

    _users_select = sqla.select([
        ddl.entity.c.id,
        ddl.entity.c.name,
        ddl.user.c.admin,
    ]).select_from(
        ddl.entity.join(
            ddl.user
        ).join(
            ddl.user_group,
            onclause=(ddl.user.c.id == ddl.user_group.c.user_id),
            isouter=True
        )
    )

    def get_users(self, group_id=None):
        stmt = self._users_select
        if group_id is not None:
            stmt = stmt.where(ddl.user_group.c.group_id == group_id)
        result = self.connection.execute(stmt)
        rows = result.fetchall()
        result.close()
        return [
            models.User(row['name'], row['id'], row['admin']) for row in rows
        ]

    _entity_insert = ddl.entity.insert()

    _user_insert = ddl.user.insert()

    def add_user(self, name, is_admin=False):
        entity_result = self.connection.execute(self._entity_insert,
                                                name=name,
                                                type='user')
        entity_id = entity_result.inserted_primary_key[0]
        entity_result.close()
        user_result = self.connection.execute(self._user_insert,
                                              id=entity_id,
                                              admin=is_admin)
        user_result.close()
        return models.User(name, entity_id, is_admin)

    _entity_update = ddl.entity.update().where(
        sqla.and_(
            ddl.entity.c.id == sqla.bindparam('id_'),
            ddl.entity.c.type == sqla.bindparam('type_')
        )
    )

    _user_update = ddl.user.update().where(
        ddl.user.c.id == sqla.bindparam('id_')
    )

    def save_user(self, user):
        entity_result = self.connection.execute(self._entity_update,
                                                id_=user.id_,
                                                type_='user',
                                                name=user.name)
        self._check_update_result('User', user.id_, entity_result)
        entity_result.close()
        user_result = self.connection.execute(self._user_update,
                                              id_=user.id_,
                                              admin=user.admin)
        self._check_update_result('User', user.id_, user_result)
        user_result.close()

    _group_select = sqla.select([
        ddl.entity.c.id,
        ddl.entity.c.name,
    ]).where(
        sqla.and_(
            ddl.entity.c.type == 'group',
            ddl.entity.c.id == sqla.bindparam('id_')
        )
    )

    def get_group(self, group_id):
        result = self.connection.execute(self._group_select,
                                         id_=group_id)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Group', group_id)
        return models.Group(row['name'], row['id'])

    _groups_select = sqla.select([
        ddl.entity.c.id,
        ddl.entity.c.name,
    ]).select_from(
        ddl.entity.join(
            ddl.user_group,
            onclause=(ddl.entity.c.id == ddl.user_group.c.group_id),
            isouter=True
        )
    ).where(
        ddl.entity.c.type == 'group'
    )

    def get_groups(self, user_id=None):
        stmt = self._groups_select
        if user_id is not None:
            stmt = stmt.where(ddl.user_group.c.user_id == user_id)
        result = self.connection.execute(stmt)
        rows = result.fetchall()
        result.close()
        return [models.Group(row['name'], row['id']) for row in rows]

    def add_group(self, name):
        result = self.connection.execute(self._entity_insert,
                                         type='group',
                                         name=name)
        return models.Group(name, result.inserted_primary_key[0])

    def save_group(self, group):
        result = self.connection.execute(self._entity_update,
                                         type_='group',
                                         id_=group.id_,
                                         name=group.name)
        self._check_update_result('Group', group.id_, result)
        result.close()

    _entity_select_both = sqla.select([
        ddl.entity.c.id,
        ddl.entity.c.name,
        ddl.entity.c.type,
        ddl.user.c.admin,
    ]).select_from(
        ddl.entity.join(
            ddl.user,
            isouter=True
        )
    ).where(
        ddl.entity.c.id == sqla.bindparam('id_')
    )

    def get_entity(self, entity_id):
        result = self.connection.execute(self._entity_select_both,
                                         id_=entity_id)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Entity', entity_id)
        if row['type'] == 'user':
            return models.User(row['name'], row['id'], row['admin'])
        elif row['type'] == 'group':
            return models.Group(row['name'], row['id'])
        else:
            raise errors.StorageError('Entity', entity_id)

    _membership_insert = ddl.user_group.insert()

    def associate_user_group(self, user_id, group_id):
        try:
            result = self.connection.execute(self._membership_insert,
                                             user_id=user_id,
                                             group_id=group_id)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_user_group_user_id_entity_id' in error_message or \
                    'ck_user_group_user_type' in error_message:
                not_found = errors.NotFoundError('User', user_id)
            elif 'fk_user_group_group_id_entity_id' in error_message or \
                    'ck_user_group_group_type' in error_message:
                not_found = errors.NotFoundError('Group', group_id)
            else:
                raise
            six.raise_from(not_found, integrity_exc)

    _membership_delete = ddl.user_group.delete().where(
        sqla.and_(
            ddl.user_group.c.user_id == sqla.bindparam('user_id'),
            ddl.user_group.c.group_id == sqla.bindparam('group_id')
        )
    )

    def disassociate_user_group(self, user_id, group_id):
        result = self.connection.execute(self._membership_delete,
                                         user_id=user_id,
                                         group_id=group_id)

    # Killmails

    _killmail_select = sqla.select([
        # We don't need to fetch all the *_type columns for all the rows,
        # they're more a consistency thing
        ddl.killmail.c.id,
        ddl.killmail.c.user_id,
        ddl.killmail.c.character_id,
        ddl.killmail.c.corporation_id,
        ddl.killmail.c.alliance_id,
        ddl.killmail.c.system_id,
        ddl.killmail.c.constellation_id,
        ddl.killmail.c.region_id,
        ddl.killmail.c.type_id,
        ddl.killmail.c.timestamp,
        ddl.killmail.c.url,
    ])

    @staticmethod
    def _killmail_from_row(row):
        killmail_kwargs = {
            key: row[key] for key in
            ('user_id', 'character_id', 'corporation_id', 'alliance_id',
             'system_id', 'constellation_id', 'region_id', 'type_id',
             'timestamp', 'url')
        }
        return models.Killmail(row['id'], **killmail_kwargs)

    def get_killmail(self, killmail_id):
        stmt = self._killmail_select.where(ddl.killmail.c.id == killmail_id)
        result = self.connection.execute(stmt)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Killmail', killmail_id)
        return self._killmail_from_row(row)

    def get_killmails(self, killmail_ids):
        stmt = self._killmail_select.where(ddl.killmail.c.id.in_(killmail_ids))
        result = self.connection.execute(stmt)
        rows = result.fetchall()
        result.close()
        # Not checking for the no results case; this method doesn't raise for
        # those.
        return [self._killmail_from_row(row) for row in rows]

    _name_insert = ddl.ccp_name.insert()

    def ensure_ccp_names(self, **kwargs):
        # This is taking advantage of CCP using unique ID number ranges for
        # various classes of things in Eve (at least for now).
        names_stmt = sqla.select([
            ddl.ccp_name.c.id,
            ddl.ccp_name.c.type,
        ]).where(
            ddl.ccp_name.c.id.in_(list(kwargs.values()))
        )
        names_result = self.connection.execute(names_stmt)
        rows = names_result.fetchall()
        names_result.close()
        # Find missing IDs, look them up and insert them
        found_ids = {row['id'] for row in rows}
        to_insert = []
        for attr_name, ccp_id in six.iteritems(kwargs):
            if ccp_id in found_ids:
                continue
            type_name = attr_name[:-3]
            # using super to skip attempting to look up the names in the DB
            # (which we just did).
            if type_name == 'character':
                method_name = 'get_ccp_character'
            else:
                method_name = 'get_{}'.format(type_name)
            getter = getattr(super(SqlStore, self), method_name)
            response = getter(**{attr_name: ccp_id})
            to_insert.append({
                'type': type_name,
                'id': response['id'],
                'name': response['name'],
            })
        if len(to_insert) > 0:
            insert_result = self.connection.execute(self._name_insert,
                                                    to_insert)
            insert_result.close()

    _killmail_insert = ddl.killmail.insert()

    def add_killmail(self, **kwargs):
        # First update the various values of ccp_name as needed
        ccp_keys = {'character_id', 'corporation_id', 'alliance_id',
                    'system_id', 'constellation_id', 'region_id', 'type_id'}
        ccp_ids = {k: v for k, v in six.iteritems(kwargs) if k in ccp_keys}
        insert_args = dict(ccp_ids)
        self.ensure_ccp_names(**ccp_ids)
        insert_args['id'] = kwargs['id_']
        insert_args['user_id'] = kwargs['user_id']
        insert_args['timestamp'] = kwargs['timestamp']
        insert_args['url'] = kwargs['url']
        try:
            result = self.connection.execute(self._killmail_insert,
                                             **insert_args)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_killmail_user_id_user_id' in error_message:
                not_found = errors.NotFoundError('User', kwargs['user_id'])
            elif 'kf_killmail_character_id_character_ccp_id' in error_message:
                not_found = errors.NotFoundError('Character',
                                                 kwargs['character_id'])
            elif 'pk_killmail' in error_message:
                # Duplicate killmail submission, just return the existing
                # killmail
                # TODO Add tests for this
                return self.get_killmail(kwargs['id_'])
            else:
                raise
            six.raise_from(not_found, integrity_exc)
        model_args = dict(insert_args)
        model_args['id_'] = model_args['id']
        del model_args['id']
        return models.Killmail(**model_args)

    # Requests

    _request_select = sqla.select([ddl.request])

    def get_request(self, request_id=None, killmail_id=None, division_id=None):
        if request_id is not None:
            stmt = self._request_select.where(ddl.request.c.id == request_id)
        elif killmail_id is not None and division_id is not None:
            stmt = self._request_select.where(
                sqla.and_(
                    ddl.request.c.killmail_id == killmail_id,
                    ddl.request.c.division_id == division_id,
                )
            )
        else:
            raise TypeError("Either request_id or both killmail_id and"
                            "division_id must be given.")
        result = self.connection.execute(stmt)
        row = result.first()
        if row is None:
            if request_id is not None:
                identitifer = str(request_id)
            else:
                identitifer = '({}, {})'.format(killmail_id, division_id)
            raise errors.NotFoundError('Request', identitifer)
        return models.Request.from_dict(row)

    _requests_select = sqla.select([ddl.request]).where(
        ddl.request.c.killmail_id == sqla.bindparam('killmail_id')
    )

    def get_requests(self, killmail_id):
        result = self.connection.execute(self._requests_select,
                                         killmail_id=killmail_id)
        rows = result.fetchall()
        result.close()
        return [models.Request.from_dict(row) for row in rows]

    _request_insert = ddl.request.insert().return_defaults(
        ddl.request.c.timestamp,
        ddl.request.c.base_payout,
        ddl.request.c.payout,
    )

    def add_request(self, killmail_id, division_id, details=u''):
        try:
            result = self.connection.execute(self._request_insert,
                                             killmail_id=killmail_id,
                                             division_id=division_id,
                                             details=details)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_request_division_id_division_id' in error_message:
                not_found = errors.NotFoundError('Division', divsion_id)
            elif 'fk_request_killmail_id_killmail_id' in error_message:
                not_found = errors.NotFoundError('Killmail', killmail_id)
            else:
                raise
            six.raise_from(not_found, integrity_exc)
        if result.returned_defaults is not None:
            request_dict = dict(result.returned_defaults)
            # Add in the other data we have form other sources
            request_dict['id'] = result.inserted_primary_key[0]
            request_dict['division_id'] = division_id
            request_dict['killmail_id'] = killmail_id
            request_dict['details'] = details
            # This is a SQLAlchemy default, not a server default, so we pull it
            # from the SQLA DDL. The attribute 'default' on the column is an
            # instance of sqlalchemy.schema.ColumnDefault, so we need to access
            # the arg attribute.
            request_dict['status'] = ddl.request.c.status.default.arg
            return models.Request.from_dict(request_dict)
        else:
            # Execute a fresh query to get the server-generated defaults
            return self.get_request(division_id=division_id,
                                    killmail_id=killmail_id)

    _request_update = ddl.request.update().where(
        sqla.and_(
            # Normally I'd put '_id' at the end of these, but I'm using these
            # names to disambiguate from the actual column names.
            ddl.request.c.killmail_id == sqla.bindparam('killmail'),
            ddl.request.c.division_id == sqla.bindparam('division')
        )
    )

    def save_request(self, request):
        result = self.connection.execute(self._request_update,
                                         division=request.division_id,
                                         killmail=request.killmail_id,
                                         details=request.details,
                                         status=request.status,
                                         base_payout=request.base_payout,
                                         payout=request.payout)
        self._check_update_result('Request', request.id_, result)
        result.close()

    # Request Actions

    _action_select = sqla.select([ddl.action]).where(
        ddl.action.c.id == sqla.bindparam('action_id')
    )

    def get_action(self, action_id):
        result = self.connection.execute(self._action_select,
                                         action_id=action_id)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Action', action_id)
        row = dict(row)
        row['contents'] = row.pop('details')
        return models.Action.from_dict(row)

    _actions_select = sqla.select([ddl.action]).where(
        ddl.action.c.request_id == sqla.bindparam('request_id')
    )

    def get_actions(self, request_id):
        result = self.connection.execute(self._actions_select,
                                         request_id=request_id)
        rows = result.fetchall()
        result.close()

        def create_action(row):
            return models.Action(row['id'],
                                 row['type'],
                                 timestamp=row['timestamp'],
                                 contents=row['details'],
                                 user_id=row['user_id'],
                                 request_id=request_id)

        return [create_action(row) for row in rows]

    _action_insert = ddl.action.insert().return_defaults(
        ddl.action.c.timestamp
    )

    def add_action(self, request_id, type_, user_id, contents=u''):
        try:
            result = self.connection.execute(self._action_insert,
                                             request_id=request_id,
                                             user_id=user_id,
                                             type=type_,
                                             details=contents)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_action_request_id_request_id' in error_message:
                not_found = errors.NotFoundError('Request', request_id)
            elif 'fk_actoin_user_id_user_id' in error_message:
                not_found = errors.NotFoundError('User', user_id)
            else:
                raise
            six.raise_from(not_found, integrity_exc)
        # Some backends support returning server generated default rows, some
        # do not. For those that don't, fetch the entire new row in a new
        # query.
        action_id = result.inserted_primary_key[0]
        result.close()
        if result.returned_defaults is not None:
            action_dict = dict(result.returned_defaults)
            action_dict.update({
                'id': action_id,
                'type': type_,
                'contents': contents,
                'user_id': user_id,
                'request_id': request_id,
            })
            return models.Action.from_dict(action_dict)
        else:
            return self.get_action(action_id=action_id)

    # Request Modifiers

    @staticmethod
    def _modifier_from_row(row):
        if row['void_user_id'] is not None:
            void = {
                'user_id': row['void_user_id'],
                'timestamp': row['void_timestamp'],
            }
        else:
            void = None
        modifier_dict = dict(row)
        if void is not None:
            modifier_dict['void'] = void
        return models.Modifier.from_dict(modifier_dict)

    _modifier_select = sqla.select([
        ddl.modifier.c.id,
        ddl.modifier.c.type,
        ddl.modifier.c.user_id,
        ddl.modifier.c.request_id,
        ddl.modifier.c.note,
        ddl.modifier.c.value,
        ddl.modifier.c.timestamp,
        ddl.void_modifier.c.user_id.label('void_user_id'),
        ddl.void_modifier.c.timestamp.label('void_timestamp'),
    ]).select_from(ddl.modifier.join(ddl.void_modifier, isouter=True))

    def get_modifier(self, modifier_id):
        stmt = self._modifier_select.where(ddl.modifier.c.id == modifier_id)
        result = self.connection.execute(stmt)
        row = result.first()
        if row is None:
            raise errors.NotFoundError('Modifier', modifier_id)
        return self._modifier_from_row(row)

    def get_modifiers(self, request_id, void=None, type_=None):
        conditions = [ddl.modifier.c.request_id ==
                      sqla.bindparam('request_id')]
        if void is not None:
            # If void is None, no filtering is done on a modifier's void state.
            # If an argument is given to void, it is evaluated on it's
            # truthiness. True values mean only voided modifiers are fetched,
            # and the opposite for false-y values.
            if void:
                conditions.append(ddl.void_modifier.c.user_id != None)
            else:
                conditions.append(ddl.void_modifier.c.user_id == None)
        if type_ is not None:
            conditions.append(ddl.modifier.c.type == type_)
        stmt = self._modifier_select.where(sqla.and_(*conditions))
        result = self.connection.execute(stmt, request_id=request_id)
        rows = result.fetchall()
        result.close()
        return [self._modifier_from_row(row) for row in rows]

    _modifier_insert = ddl.modifier.insert().return_defaults(
        ddl.modifier.c.timestamp
    )

    def add_modifier(self, request_id, user_id, type_, value, note=u''):
        try:
            result = self.connection.execute(self._modifier_insert,
                                             request_id=request_id,
                                             user_id=user_id,
                                             type=type_,
                                             value=value,
                                             note=note)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_modifier_request_id_request_id' in error_message:
                not_found = errors.NotFoundError('Request', request_id)
            elif 'fk_modifier_user_id_user_id' in error_message:
                not_found = errors.NotFoundError('User', user_id)
            else:
                raise
            six.raise_from(not_found, integrity_exc)
        modifier_id = result.inserted_primary_key[0]
        if result.returned_defaults is not None:
            modifier_dict = {
                'id': modifier_id,
                'type': type_,
                'value': value,
                'user_id': user_id,
                'request_id': request_id,
                'note': note,
            }
            modifier_dict.update(result.returned_defaults)
            result.close()
            return models.Modifier.from_dict(modifier_dict)
        else:
            result.close()
            return self.get_modifier(modifier_id)

    # Not returning defaults, as we don't return anything from void_modifier()
    _void_modifier_insert = ddl.void_modifier.insert()

    def void_modifier(self, modifier_id, user_id):
        try:
            result = self.connection.execute(self._void_modifier_insert,
                                             modifier_id=modifier_id,
                                             user_id=user_id)
        except sqla.exc.IntegrityError as integrity_exc:
            error_message = str(integrity_exc.orig)
            if 'fk_void_modifier_modifier_id_modifier_id' in error_message:
                new_exc = errors.NotFoundError('Modifier', modifier_id)
            elif 'fk_void_modifier_user_id_user_id' in error_message:
                new_exc = errors.NotFoundError('User', user_id)
            elif 'pk_void_modifier' in error_message:
                new_exc = errors.VoidedModifierError(modifier_id)
            else:
                raise
            six.raise_from(new_exc, integrity_exc)

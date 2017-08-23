from __future__ import absolute_import

import itertools

import six
import sqlalchemy as sqla

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
        result = self.connection.execute(self._authn_insert,
                                         type=type_,
                                         entity_id=entity_id,
                                         provider_key=provider_key,
                                         provider_uuid=provider_uuid,
                                         data=extra_data)
        return self._get_authn(type_, provider_uuid, provider_key)

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
        # TODO check result somehow

    def get_authn_user(self, provider_uuid, provider_key):
        """Get an :py:class:`~.AuthenticatedUser` from storage.

        If a user is unable to be found for the provided provider and key, the
        string `u'not found'` will be present in the errors array.

        :param provider_uuid: The UUID for the
            :py:class:`~.AuthenticationProvider` for this
            :py:class:`~.AuthenticatedUser`.
        :type provider_uuid: :py:class:`uuid.UUID`
        :param str provider_key: The key identifying a unique user to the
            authentication provider.
        :return: The user (if found).
        :rtype: :py:class:`~.AuthenticatedUser` or `None`
        """
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

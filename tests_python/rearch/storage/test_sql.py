import datetime as dt
import decimal
import uuid

import pytest
import sqlalchemy as sqla

from evesrp import new_models as models
from evesrp.storage.sql import SqlStore, ddl
from evesrp.util import utc
from .base_test import CommonStorageTest


class TestSqlStore(CommonStorageTest):

    @pytest.fixture(
        scope='session',
        params=(
            #'sqlite:///:memory:',
            'postgres://paxswill@localhost/evesrp_rearch',
        ),
        ids=(
            #'sqlite',
            'postgres',
        )
    )
    def engine(self, request):
        engine = sqla.create_engine(request.param)
        return engine

    @pytest.fixture(scope='session')
    def schema(self, engine):
        # Destroy first to clear up any leftover data
        SqlStore.destroy(engine)
        SqlStore.create(engine)
        yield
        SqlStore.destroy(engine)

    def populate_database(self, conn):
        conn.execute(
            ddl.entity.insert(),
            [
                {'id': 9, 'type': 'user', 'name': u'User 9'},
                {'id': 2, 'type': 'user', 'name': u'User 2'},
                {'id': 7, 'type': 'user', 'name': u'User 7'},
                {'id': 3000, 'type': 'group', 'name': u'Group 3000'},
                {'id': 4000, 'type': 'group', 'name': u'Group 4000'},
                {'id': 5000, 'type': 'group', 'name': u'Group 5000'},
                {'id': 6000, 'type': 'group', 'name': u'Group 6000'},
            ]
        )
        conn.execute(
            ddl.authn_entity.insert(),
            [
                {
                    'type': 'user',
                    'provider_uuid':
                        uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
                    'provider_key': 'authn_user',
                    'entity_id': 9,
                },
                {
                    'type': 'group',
                    'provider_uuid':
                        uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
                    'provider_key': 'authn_group',
                    'entity_id': 3000,
                },
            ]
        )
        conn.execute(
            ddl.user.insert(),
            [
                {'id': 9, 'admin': False},
                {'id': 2, 'admin': True},
                {'id': 7, 'admin': False},
            ]
        )
        conn.execute(
            ddl.user_group.insert(),
            [
                {'group_id': 3000, 'user_id': 9},
                {'group_id': 4000, 'user_id': 2},
                {'group_id': 5000, 'user_id': 9},
                {'group_id': 5000, 'user_id': 2},
            ]
        )
        conn.execute(
            ddl.division.insert(),
            [
                {'id': 10, 'name': u'Testing Division'},
                {'id': 30, 'name': u'YATD: Yet Another Testing Division'},
            ]
        )
        conn.execute(
            ddl.permission.insert(),
            [
                {'division_id': 30, 'entity_id': 2, 'type':
                 models.PermissionType.pay},
                {'division_id': 10, 'entity_id': 9, 'type':
                 models.PermissionType.submit},
                {'division_id': 30, 'entity_id': 5000, 'type':
                 models.PermissionType.submit},
                {'division_id': 10, 'entity_id': 7, 'type':
                 models.PermissionType.review},
                {'division_id': 30, 'entity_id': 7, 'type':
                 models.PermissionType.review},
            ]
        )
        conn.execute(
            ddl.note.insert(),
            [
                {
                    'id': 1,
                    'subject_id': 9,
                    'submitter_id': 7,
                    'timestamp': dt.datetime(2017, 4, 1, tzinfo=utc),
                    'content': (u'Not the sharpest tool in the shed. Keeps '
                                 u'losing things, deny future requests.'),
                }
            ]
        )
        conn.execute(
            ddl.ccp_name.insert(),
            [
                {'type': 'character', 'id': 2112311608,
                 'name': u'marssell kross'},
                {'type': 'character', 'id': 570140137, 'name': u'Paxswill'},
                # Corporations
                {'type': 'corporation', 'id': 1018389948, 'name': u'Dreddit'},
                {'type': 'corporation', 'id': 1000166,
                 'name': u'Imperial Academy'},
                # Alliances
                {'type': 'alliance', 'id': 498125261,
                 'name': u'Test Alliance Please Ignore'},
                # Solar Systems
                {'type': 'system', 'id': 30000848, 'name': u'M-OEE8'},
                {'type': 'system', 'id': 31002586, 'name': u'J000327'},
                {'type': 'system', 'id': 30045316, 'name': u'Innia'},
                {'type': 'system', 'id': 30003837, 'name': u'Aldranette'},
                # Constellations
                {'type': 'constellation', 'id': 20000124, 'name': u'1P-VL2'},
                {'type': 'constellation', 'id': 21000332,
                 'name': u'H-C00332'},
                {'type': 'constellation', 'id': 20000783, 'name': u'Inolari'},
                {'type': 'constellation', 'id': 20000561, 'name': u'Amevync'},
                # Regions
                {'type': 'region', 'id': 10000010, 'name': u'Tribute'},
                {'type': 'region', 'id': 11000032, 'name': u'H-R00032'},
                {'type': 'region', 'id': 10000069, 'name': u'Black Rise'},
                {'type': 'region', 'id': 10000048, 'name': u'Placid'},
                # Types
                {'type': 'type', 'id': 4310, 'name': u'Tornado'},
                {'type': 'type', 'id': 605, 'name': u'Heron'},
                {'type': 'type', 'id': 593, 'name': u'Tristan'},
            ]
        )
        conn.execute(
            ddl.character.insert(),
            [
                {'ccp_id': 2112311608, 'user_id': 9},
                {'ccp_id': 570140137, 'user_id': 9},
            ]
        )
        conn.execute(
            ddl.killmail.insert(),
            [
                {
                    'id': 52861733,
                    'type_id': 4310,
                    'user_id': 9,
                    'character_id': 570140137,
                    'corporation_id': 1018389948,
                    'alliance_id': 498125261,
                    'system_id': 30000848,
                    'constellation_id': 20000124,
                    'region_id': 10000010,
                    'timestamp': dt.datetime(2016, 3, 28, 2, 32, 50,
                                             tzinfo=utc),
                    'url': u'https://zkillboard.com/kill/52861733/',
                },
                {
                    'id': 60713776,
                    'type_id': 605,
                    'user_id': 2,
                    'character_id': 2112311608,
                    'corporation_id': 1000166,
                    'alliance_id': None,
                    'system_id': 31002586,
                    'constellation_id': 21000332,
                    'region_id': 11000032,
                    'timestamp': dt.datetime(2017, 3, 12, 0, 33, 10,
                                             tzinfo=utc),
                    'url': u'https://zkillboard.com/kill/60713776/',
                },
                {
                    'id': 53042210,
                    'type_id': 593,
                    'user_id': 9,
                    'character_id': 570140137,
                    'corporation_id': 1018389948,
                    'alliance_id': 498125261,
                    'system_id': 30045316,
                    'constellation_id': 20000783,
                    'region_id': 10000069,
                    'timestamp': dt.datetime(2016, 4, 4, 17, 58, 45,
                                             tzinfo=utc),
                    'url': u'https://zkillboard.com/kill/53042210/',
                },
                {
                    'id': 53042755,
                    'type_id': 593,
                    'user_id': 9,
                    'character_id': 570140137,
                    'corporation_id': 1018389948,
                    'alliance_id': 498125261,
                    'system_id': 30003837,
                    'constellation_id': 20000561,
                    'region_id': 10000048,
                    'timestamp': dt.datetime(2016, 4, 4, 18, 19, 27,
                                             tzinfo=utc),
                    'url': u'https://zkillboard.com/kill/53042755/',
                },
            ]
        )
        conn.execute(
            ddl.request.insert(),
            [
                {
                    'id': 123,
                    'killmail_id': 52861733,
                    'division_id': 10,
                    'details': u'Hey! I lost a Windrunner.',
                    'timestamp': dt.datetime(2016, 3, 30, 9, 30, tzinfo=utc),
                    'base_payout': decimal.Decimal(5000000),
                    'payout': decimal.Decimal(5500000),
                    'status': models.ActionType.rejected,
                },
                {
                    'id': 456,
                    'killmail_id': 52861733,
                    'division_id': 30,
                    'details': (u'I deserve money from this division as well, '
                                u'please'),
                    'timestamp': dt.datetime(2017, 3, 10, 10, 11, 12,
                                             tzinfo=utc),
                    'base_payout': decimal.Decimal(7000000),
                    'payout': decimal.Decimal(3500000),
                    'status': models.ActionType.evaluating,
                },
                {
                    'id': 789,
                    'killmail_id': 60713776,
                    'division_id': 30,
                    'details': (u"I'm an explorer who lost a Heron. Gimme "
                                u"money."),
                    'timestamp': dt.datetime(2017, 3, 15, 13, 27, tzinfo=utc),
                    'base_payout': decimal.Decimal(5000000),
                    'payout': decimal.Decimal(50000),
                    'status': models.ActionType.approved,
                },
                {
                    'id': 234,
                    'killmail_id': 53042210,
                    'division_id': 30,
                    'details': u"Fund my solo PvP Tristans.",
                    'timestamp': dt.datetime(2017, 4, 10, tzinfo=utc),
                    'base_payout': decimal.Decimal(5000000),
                    'payout': decimal.Decimal(5000000),
                    'status': models.ActionType.incomplete,
                },
                {
                    'id': 345,
                    'killmail_id': 53042755,
                    'division_id': 10,
                    'details': u"iskies for my toonies. Please",
                    'timestamp': dt.datetime(2017, 4, 9, tzinfo=utc),
                    'base_payout': decimal.Decimal(5000000),
                    'payout': decimal.Decimal(5000000),
                    'status': models.ActionType.incomplete,
                },
            ]
        )
        conn.execute(
            ddl.action.insert(),
            [
                {
                    'id': 10000,
                    'type': models.ActionType.rejected,
                    'timestamp': dt.datetime(2016, 4, 3, tzinfo=utc),
                    'details': u'git gud scrub',
                    'user_id': 7,
                    'request_id': 123,
                },
                {
                    'id': 20000,
                    'type': models.ActionType.comment,
                    'timestamp': dt.datetime(2016, 4, 3, 1, tzinfo=utc),
                    'details': u'sadface',
                    'user_id': 9,
                    'request_id': 123,
                },
                {
                    'id': 30000,
                    'type': models.ActionType.approved,
                    'timestamp': dt.datetime(2017, 4, 3, 1, tzinfo=utc),
                    'details': u'',
                    'user_id': 7,
                    'request_id': 789,
                },
            ]
        )
        conn.execute(
            ddl.modifier.insert(),
            [
                {
                    'id': 100000,
                    'type': models.ModifierType.absolute,
                    'value': decimal.Decimal(500000),
                    'note': u'For something good',
                    'timestamp': dt.datetime(2016, 4, 1, tzinfo=utc),
                    'user_id': 7,
                    'request_id': 123,
                    'void_user_id': None,
                    'void_timestamp': None,
                },
                {
                    'id': 200000,
                    'type': models.ModifierType.absolute,
                    'value': decimal.Decimal(500000),
                    'note': u'Incorrect bonus',
                    'timestamp': dt.datetime(2017, 3, 11, 1, 0, tzinfo=utc),
                    'user_id': 7,
                    'request_id': 456,
                    'void_user_id': 7,
                    'void_timestamp': dt.datetime(2017, 3, 11, 1, 5,
                                                  tzinfo=utc),
                },
                {
                    'id': 300000,
                    'type': models.ModifierType.relative,
                    'value': decimal.Decimal('-0.5'),
                    'note': u'You dun goofed',
                    'timestamp': dt.datetime(2017, 3, 11, 1, 7, tzinfo=utc),
                    'user_id': 7,
                    'request_id': 456,
                    'void_user_id': None,
                    'void_timestamp': None,
                },
                {
                    'id': 400000,
                    'type': models.ModifierType.relative,
                    'value': decimal.Decimal('-0.5'),
                    'note': u'Major deduction',
                    'timestamp': dt.datetime(2017, 3, 16, 1, 7, tzinfo=utc),
                    'user_id': 7,
                    'request_id': 789,
                    'void_user_id': None,
                    'void_timestamp': None,
                },
                {
                    'id': 500000,
                    'type': models.ModifierType.relative,
                    'value': decimal.Decimal('-0.49'),
                    'note': u'Almost overkill',
                    'timestamp': dt.datetime(2017, 3, 16, 1, 7, tzinfo=utc),
                    'user_id': 7,
                    'request_id': 789,
                    'void_user_id': None,
                    'void_timestamp': None,
                },
            ]
        )

    @pytest.fixture(scope='function')
    def store(self, engine, schema):
        conn = engine.connect()
        with conn.begin_nested() as trans:
            store = SqlStore(connection=conn)
            yield store
            trans.rollback()

    @pytest.fixture(scope='function')
    def populated_store(self, engine, store):
        # Peek into the store so we can stay within the nested transaction
        # started in the `store` fixture
        conn = store.connection
        with conn.begin_nested() as trans:
            self.populate_database(conn)
            yield store
            trans.rollback()

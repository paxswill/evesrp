from __future__ import absolute_import
import datetime as dt
from decimal import Decimal
import uuid

import pytest

from evesrp import storage
from evesrp import new_models as models
from .base_test import CommonStorageTest


class TestMemoryStore(CommonStorageTest):

    @pytest.fixture
    def store(self):
        return storage.MemoryStore()

    @pytest.fixture
    def populated_store(self, store):
        store._data['authn_users'].update({
            (
                uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
                'authn_user'
            ): {
                'user_id': 987,
                'extra_data': {},
            },
        })
        store._data['authn_groups'].update({
            (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
             'authn_group'): {
                'group_id': 876,
                'extra_data': {},
            },
        })
        store._data['users'].update({
            9: {
                'id': 9,
                'name': u'User 9',
                'is_admin': False,
            },
            2: {
                'id': 2,
                'name': u'User 2',
                'is_admin': True,
            },
            7: {
                'id': 7,
                'name': u'User 7',
                'is_admin': False,
            },
        })
        store._data['groups'].update({
            3000: {
                'id': 3000,
                'name': u'Group 3000',
            },
            4000: {
                'id': 4000,
                'name': u'Group 4000',
            },
            5000: {
                'id': 5000,
                'name': u'Group 5000',
            },
            6000: {
                'id': 6000,
                'name': u'Group 6000',
            },
        })
        store._data['group_members'].update({
            3000: {9, },
            4000: {2, },
            5000: {2, 9},
            6000: set(),
        })
        store._data['divisions'].update({
            10: {
                'id': 10,
                'name': u'Testing Division',
            },
            30: {
                'id': 30,
                'name': u'YATD: Yet Another Testing Division',
            },
        })
        store._data['permissions'].update({
            models.Permission(30, 2, models.PermissionType.pay),
            models.Permission(10, 9, models.PermissionType.submit),
            models.Permission(30, 5000, models.PermissionType.submit),
            models.Permission(10, 7, models.PermissionType.review),
            models.Permission(30, 7, models.PermissionType.review),
        })
        store._data['characters'].update({
            2112311608: {
                # See note above about differing user_ids
                'user_id': 9,
                'id': 2112311608,
                'name': u'marssell kross'
            },
            570140137: {
                'user_id': 9,
                'id': 570140137,
                'name': u'Paxswill',
            },
        })
        store._data['killmails'].update({
            52861733: {
                'id': 52861733,
                'type_id': 4310,
                'user_id': 9,
                'character_id': 570140137,
                'corporation_id': 1018389948,
                'alliance_id': 498125261,
                'system_id': 30000848,
                'constellation_id': 20000124,
                'region_id': 10000010,
                'timestamp': dt.datetime(2016, 3, 28, 2, 32, 50),
                'url': u'https://zkillboard.com/kill/52861733/',
            },
            # Recent kill I found on zKB that wasn't in an alliance
            60713776: {
                'id': 60713776,
                'type_id': 605,
                # Putting the kill's user_id and the character's current
                # user_id different (use case where a character was transferred
                # after this request was submitted).
                'user_id': 2,
                'character_id': 2112311608,
                'corporation_id': 1000166,
                'alliance_id': None,
                'system_id': 31002586,
                'constellation_id': 21000332,
                'region_id': 11000032,
                'timestamp': dt.datetime(2017, 3, 12, 0, 33, 10),
                'url': u'https://zkillboard.com/kill/60713776/',
            },
        })
        store._data['requests'].update({
            123: {
                'id': 123,
                'killmail_id': 52861733,
                'division_id': 10,
                'details': u'Hey! I lost a Windrunner.',
                'timestamp': dt.datetime(2016, 3, 30, 9, 30),
                'base_payout': Decimal(5000000),
                'payout': Decimal(5500000),
                'status': models.ActionType.rejected,
            },
            456: {
                'id': 456,
                'killmail_id': 52861733,
                'division_id': 30,
                'details': u'I deserve money from this division as well',
                'timestamp': dt.datetime(2017, 3, 10, 10, 11, 12),
                'base_payout': Decimal(7000000),
                'payout': Decimal(3500000),
                'status': models.ActionType.evaluating,
            },
            789: {
                'id': 789,
                'killmail_id': 60713776,
                'division_id': 30,
                'details': u"I'm an explorer who lost a Heron. Gimme money.",
                'timestamp': dt.datetime(2017, 3, 15, 13, 27),
                'base_payout': Decimal(5000000),
                'payout': Decimal(50000),
                'status': models.ActionType.approved,
            },
        })
        store._data['actions'].update({
            10000: {
                'id': 10000,
                'type': models.ActionType.rejected,
                'timestamp': dt.datetime(2016, 4, 3),
                'contents': u'git gud scrub',
                'user_id': 7,
                'request_id': 123,
            },
            20000: {
                'id': 20000,
                'type': models.ActionType.comment,
                'timestamp': dt.datetime(2016, 4, 3, 1),
                'contents': u'sadface',
                'user_id': 9,
                'request_id': 123,
            },
            30000: {
                'id': 30000,
                'type': models.ActionType.approved,
                'timestamp': dt.datetime(2017, 4, 3, 1),
                'contents': u'',
                'user_id': 7,
                'request_id': 789,
            },
        })
        store._data['modifiers'].update({
            100000: {
                'id': 100000,
                'type': models.ModifierType.absolute,
                'value': Decimal(500000),
                'note': u'For something good',
                'timestamp': dt.datetime(2016, 4, 1),
                'user_id': 7,
                'request_id': 123,
                'void': None,
            },
            200000: {
                'id': 200000,
                'type': models.ModifierType.absolute,
                'value': Decimal(500000),
                'note': u'Incorrect bonus',
                'timestamp': dt.datetime(2017, 3, 11, 1, 0),
                'user_id': 7,
                'request_id': 456,
                'void': {
                    'user_id': 7,
                    'timestamp': dt.datetime(2017, 3, 11, 1, 5),
                },
            },
            300000: {
                'id': 300000,
                'type': models.ModifierType.relative,
                'value': Decimal('-0.5'),
                'note': u'You dun goofed',
                'timestamp': dt.datetime(2017, 3, 11, 1, 7),
                'user_id': 7,
                'request_id': 456,
                'void': None,
            },
            400000: {
                'id': 400000,
                'type': models.ModifierType.relative,
                'value': Decimal('-0.5'),
                'note': u'Major deduction',
                'timestamp': dt.datetime(2017, 3, 16, 1, 7),
                'user_id': 7,
                'request_id': 789,
                'void': None,
            },
            500000: {
                'id': 500000,
                'type': models.ModifierType.relative,
                'value': Decimal('-0.49'),
                'note': u'Almost overkill',
                'timestamp': dt.datetime(2017, 3, 16, 1, 7),
                'user_id': 7,
                'request_id': 789,
                'void': None,
            },
        })
        store._data['notes'].update({
            9: [
                {
                    'id': 1,
                    'submitter_id': 7,
                    'subject_id': 9,
                    'timestamp': dt.datetime(2017, 4, 1),
                    'contents': (u'Not the sharpest tool in the shed. Keeps '
                                 u'losing things, deny future requests.'),
                },
            ],
        })
        return store

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import datetime as dt
from decimal import Decimal
from itertools import product, cycle
from flask import json
from evesrp import db
from evesrp.models import Request, ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp.util.datetime import utc
from evesrp.util.decimal import PrettyDecimal
from ...util import TestLogin


class TestFilterBase(TestLogin):

    DIV_1 = 'Division One'
    DIV_2 = 'Division Two'
    DIV_3 = 'Division Three'

    killmails = [
        {
            'id': 42513498,
            'ship_type': 'Scythe',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/42513498/',
            'base_payout': 22000000,
            'kill_timestamp': dt.datetime(2014, 11, 20, 4, 2,
                tzinfo=utc),
            'system': 'B-3QPD',
            'constellation': 'UX3-N2',
            'region': 'Catch',
            'pilot': 'Paxswill',
            'division': DIV_2,
            'details': 'lol Stratop',
            'status': ActionType.paid,
        },
        {
            'id': 39697412,
            'ship_type': 'Tristan',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/39697412/',
            'base_payout': 9100000,
            'kill_timestamp': dt.datetime(2014, 6, 23, 20, 6,
                tzinfo=utc),
            'system': 'Hikkoken',
            'constellation': 'Ishaga',
            'region': 'Black Rise',
            'pilot': 'Paxswill',
            'division': DIV_3,
            'details': 'Elite Solo PVP',
            'status': ActionType.evaluating,
        },
        {
            'id': 39988492,
            'ship_type': 'Crow',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/39988492/',
            'base_payout': 22000000,
            'kill_timestamp': dt.datetime(2014, 7, 9, 18, 22,
                tzinfo=utc),
            'system': 'Sadana',
            'constellation': 'Mareerieh',
            'region': 'Aridia',
            'pilot': 'Paxswill',
            'division': DIV_2,
            'details': 'Not so travel interceptor',
            'status': ActionType.approved,
        },
        {
            'id': 43292478,
            'ship_type': 'Guardian',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/43292478/',
            'base_payout': 289700000,
            'kill_timestamp': dt.datetime(2014, 12, 22, 4, 6,
                tzinfo=utc),
            'system': 'RNF-YH',
            'constellation': 'JZV-O6',
            'region': 'Catch',
            'pilot': 'Paxswill',
            'division': DIV_2,
            'details': 'lol Stratop',
            'status': ActionType.incomplete,
        },
        {
            'id': 43500358,
            'ship_type': 'Talwar',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/43500358/',
            'base_payout': 13700000,
            'kill_timestamp': dt.datetime(2014, 12, 31, 1, 48,
                tzinfo=utc),
            'system': 'Todifrauan',
            'constellation': 'Aldodan',
            'region': 'Metropolis',
            'pilot': 'DurrHurrDurr',
            'division': DIV_2,
            'details': 'Bar',
            'status': ActionType.evaluating,
        },
        {
            'id': 43162254,
            'ship_type': 'Cormorant',
            'corporation': 'Dreddit',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/43162254/',
            'base_payout': 11400000,
            'kill_timestamp': dt.datetime(2014, 12, 17, 3, 31,
                tzinfo=utc),
            'system': 'GE-8JV',
            'constellation': '9HXQ-G',
            'region': 'Catch',
            'pilot': 'DurrHurrDurr',
            'division': DIV_2,
            'details': 'lol Stratop',
            'status': ActionType.approved,
        },
        {
            'id': 31952048,
            'ship_type': 'Amarr Shuttle',
            'corporation': 'Science and Trade Institute',
            'killmail_url': 'https://zkillboard.com/kill/31952048/',
            'base_payout': 14000,
            'kill_timestamp': dt.datetime(2013, 7, 16, 4, 39,
                tzinfo=utc),
            'system': 'Karan',
            'constellation': 'Selonat',
            'region': 'Aridia',
            'pilot': 'Gevlon Goblin',
            'division': DIV_1,
            'details': 'grr goons',
            'status': ActionType.approved,
        },
        {
            'id': 41094133,
            'ship_type': 'Crucifier',
            'corporation': 'Unholy Knights of Cthulu',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/41094133/',
            'base_payout': 8300000,
            'kill_timestamp': dt.datetime(2014, 9, 6, 1, 32,
                tzinfo=utc),
            'system': 'Nisuwa',
            'constellation': 'Okakuola',
            'region': 'Black Rise',
            'pilot': 'Sapporo Jones',
            'division': DIV_2,
            'details': 'Elite Solo PVP',
            'status': ActionType.rejected,
        },
        {
            'id': 43341679,
            'ship_type': 'Vexor',
            'corporation': 'Unholy Knights of Cthulu',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/43341679/',
            'base_payout': 39900000,
            'kill_timestamp': dt.datetime(2014, 12, 24, 7, 9,
                tzinfo=utc),
            'system': '4-CM8I',
            'constellation': 'DITJ-X',
            'region': 'Scalding Pass',
            'pilot': 'Sapporo Jones',
            'division': DIV_1,
            'details': 'Scouting',
            'status': ActionType.evaluating,
        },
        {
            'id': 43372860,
            'ship_type': 'Imperial Navy Slicer',
            'corporation': 'Unholy Knights of Cthulu',
            'alliance': 'Test Alliance Please Ignore',
            'killmail_url': 'https://zkillboard.com/kill/43372860/',
            'base_payout': 15660000,
            'kill_timestamp': dt.datetime(2014, 12, 26, 0, 0,
                tzinfo=utc),
            'system': '8QT-H4',
            'constellation': 'MPJW-6',
            'region': 'Querious',
            'pilot': 'Paxswill',
            'division': DIV_1,
            'details': 'Elite Solo PVP',
            'status': ActionType.incomplete,
        },
        {
            'id': 43975437,
            'ship_type': 'Tristan',
            'corporation': 'Brave Operations - Lollipop Division',
            'alliance': 'Brave Collective',
            'killmail_url': 'https://zkillboard.com/kill/43975437/',
            'base_payout': 4800000,
            'kill_timestamp': dt.datetime(2015, 1, 18, 18, 25,
                tzinfo=utc),
            'system': 'YHN-3K',
            'constellation': 'UX3-N2',
            'region': 'Catch',
            'pilot': 'Zora Aran',
            'division': DIV_3,
            'details': 'Awox?',
            'status': ActionType.rejected,
        },
    ]

    def setUp(self):
        super(TestFilterBase, self).setUp()
        with self.app.test_request_context():
            # Divisions
            divisions = {
                self.DIV_1: Division(self.DIV_1),
                self.DIV_2: Division(self.DIV_2),
                self.DIV_3: Division(self.DIV_3),
            }
            # Give all permissions in all divisions to admin_user
            for division in divisions.values():
                for permission in PermissionType.all:
                    Permission(division, permission, self.admin_user)
            # Pilots
            pilots = {
                'Paxswill': 570140137,
                'Sapporo Jones': 772506501,
                'DurrHurrDurr': 1456384556,
                'Gevlon Goblin': 91662677,
                'Zora Aran': 534674271,
            }
            for name, id in pilots.items():
                if id % 2 == 0:
                    user = self.normal_user
                else:
                    user = self.admin_user
                db.session.add(Pilot(user, name, id))
            # Lossmails/requests
            for request_data in self.killmails:
                # Copy dict before we pop stuff out of it
                data_copy = dict(request_data)
                # Distribute requests between users 
                if request_data['id'] % 2 == 0:
                    user = self.admin_user
                else:
                    user = self.normal_user
                details = data_copy.pop('details')
                division = divisions[data_copy.pop('division')]
                status = data_copy.pop('status')
                data_copy['pilot_id'] = pilots[data_copy.pop('pilot')]
                request = Request(user, details, division, data_copy.items())
                # Set status after the base payout has been set
                request.status = status
            db.session.commit()

    def check_filter_url(self, url, expected_ids, expected_total):
        client = self.login(self.admin_name)
        resp = client.get(url, headers={'Accept':'application/json'},
                follow_redirects=False)
        if resp.status_code == 301:
            # Manually follow redirects to keep the Accept header around.
            resp = client.get(resp.location,
                    headers={'Accept':'application/json'},
                    follow_redirects=False)
        resp_obj = json.loads(resp.data)
        # Check that the returned requests match
        self.assertEqual(expected_ids,
                {request['id'] for request in resp_obj['requests']})
        # Check that the totals add up properly (in a roundabout way)
        self.assertEqual(PrettyDecimal(expected_total).currency(),
                resp_obj['total_payouts'])


class TestExactFilter(TestFilterBase):

    choices = [None]

    def test_exact_filter_combos(self):
        # Explanation for the below: product(seq, repeat=n) computes a
        # cartesian product of sequence seq against itself n times. By using
        # this as a constructor to frozenset, we can combinations with repeated
        # choices (ex: ['Foo', 'Foo'] as opposed to ['Bar', 'Foo']). frozenset
        # is used as set() is mutable, and thus unhashable. This is all wrapped
        # in a set comprehension to deduplicate combinations that differ only
        # in ordering (ex: ['Foo', 'Bar'] and ['Bar', 'Foo']).
        choice_combos = {frozenset(combo) for combo in product(self.choices,
            repeat=2)}
        for combo in choice_combos:
            # Find the set of matching killmail IDs first
            matching_ids = set()
            total_payout = Decimal(0)
            for request in self.killmails:
                if combo == {None} or request.get(self.attribute) in combo:
                    matching_ids.add(request['id'])
                    if request['status'] != ActionType.rejected:
                        total_payout += Decimal(request['base_payout'])
            # Ask the app what it thinks the matching requests are
            if combo != {None}:
                if self.attribute == 'ship_type':
                    filter_attribute = 'ship'
                else:
                    filter_attribute = self.attribute
                if self.attribute == 'status':
                    values = ','.join(map(lambda x: x.value, combo))
                else:
                    values = ','.join(combo)
                url = '/request/all/{}/{}'.format(filter_attribute, values)
            else:
                url = '/request/all/'
            self.check_filter_url(url, matching_ids, total_payout)


class TestDivisionFilter(TestExactFilter):

    attribute = 'division'

    choices = [TestFilterBase.DIV_1, TestFilterBase.DIV_2, TestFilterBase.DIV_3]


class TestAllianceFilter(TestExactFilter):

    attribute = 'alliance'

    choices = [
        'Test Alliance Please Ignore',
        'Brave Collective',
        'Goonswarm Federation',
    ]


class TestCorporationFilter(TestExactFilter):

    attribute = 'corporation'

    choices = [
        'Dreddit',
        'Unholy Knights of Cthulu',
        'Goonwaffe',
        'Science and Trade Institute',
        'Brave Collective - Lollipop Division',
    ]


class TestPilotFilter(TestExactFilter):

    attribute = 'pilot'

    choices = [
        'Paxswill',
        'DurrHurrDurr',
        'Gevlon Goblin',
        'Sapporo Jones',
        'Zora Aran',
    ]


class TestShipFilter(TestExactFilter):

    attribute = 'ship_type'

    choices = ['Tristan', 'Crow', 'Vexor', 'Guardian']


class TestRegionFilter(TestExactFilter):

    attribute = 'region'

    choices = ['Black Rise', 'Catch', 'Aridia', 'Scalding Pass']


class TestConstellationFilter(TestExactFilter):

    attribute = 'constellation'

    choices = ['UX3-N2', 'Ishaga', 'Mareerieh', '9HXQ-G', 'Selonat']


class TestSystemFilter(TestExactFilter):

    attribute = 'system'

    choices = ['GE-8JV', 'Todifrauan', 'RNF-YH', '4-CM8I', 'Karan']


class TestStatusFilter(TestExactFilter):

    attribute = 'status'

    choices = ActionType.statuses


class TestMultipleFilter(TestFilterBase):

    choices = {}

    def test_exact_multiple_filters(self):
        # Compute expected values
        matching_ids = set()
        total_payout = Decimal(0)
        for request in self.killmails:
            for attribute, valid_values in self.choices.items():
                if request.get(attribute) not in valid_values:
                    break
            else:
                matching_ids.add(request['id'])
                if request['status'] != ActionType.rejected:
                    total_payout += request['base_payout']
        # Ask the app what it thinks is the answer
        url = '/request/all/'
        for attribute, values in self.choices.items():
            url += '{}/{}/'.format(attribute, ','.join(values))
        self.check_filter_url(url, matching_ids, total_payout)


class TestDredditCatchFilter(TestMultipleFilter):

    choices = {
        'corporation': ['Dreddit'],
        'region': ['Catch'],
    }

from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from bs4 import BeautifulSoup
from evesrp import db
from evesrp.models import Request, ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from ...util import TestLogin


class TestRequestList(TestLogin):

    def setUp(self):
        super(TestRequestList, self).setUp()
        with self.app.test_request_context():
            d1 = Division('Division 1')
            d2 = Division('Division 2')
            user1 = self.normal_user
            user2 = self.admin_user
            # user1 can submit to division 1, user2 to division 2
            # user2 can review and pay out both divisions
            Permission(d1, PermissionType.submit, user1)
            Permission(d2, PermissionType.submit, user2)
            for permission in PermissionType.elevated:
                for division in (d1, d2):
                    Permission(division, permission, user2)
            Pilot(user1, 'Generic Pilot', 1)
            request_data = {
                'ship_type': 'Revenant',
                'corporation': 'Center of Applied Studies',
                'kill_timestamp': dt.datetime.utcnow(),
                'system': 'Jita',
                'constellation': 'Kimotoro',
                'region': 'The Forge',
                'pilot_id': 1,
            }
            for division, user in ((d1, user1), (d2, user2)):
                # 2 evaluating, 1 incomplete, 2 approved, 1 rejected,
                # and 1 paid.
                Request(user, 'First', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.evaluating)
                Request(user, 'Second', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.evaluating)
                Request(user, 'Third', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.incomplete)
                Request(user, 'Fourth', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.approved)
                Request(user, 'Fifth', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.approved)
                Request(user, 'Sixth', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.rejected)
                Request(user, 'Sixth', division, request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=ActionType.paid)
            db.session.commit()

    def count_requests(self, data):
        raise NotImplemented

    def accessible_list_checker(self, user_name, path, expected):
        client = self.login(user_name)
        resp = client.get(path, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.count_requests(resp.get_data()), expected)

    def elevated_list_checker(self, path, expected):
        norm_client = self.login(self.normal_name)
        norm_resp = norm_client.get(path, follow_redirects=True)
        self.assertEqual(norm_resp.status_code, 403)
        self.accessible_list_checker(self.admin_name, path, expected)


class TestTableRequestLists(TestRequestList):

    def count_requests(self, data):
        soup = BeautifulSoup(data)
        request_id_cols = soup.find_all('td',
                attrs={'data-attribute': 'status'})
        return len(request_id_cols)

    def test_pending(self):
        self.elevated_list_checker('/request/pending/', 10)

    def test_complete(self):
        self.elevated_list_checker('/request/completed/', 4)

    def test_personal(self):
        self.accessible_list_checker(self.normal_name, '/request/personal/', 7)
        self.accessible_list_checker(self.admin_name, '/request/personal/', 7)


class TestPayoutList(TestRequestList):

    def count_requests(self, data):
        soup = BeautifulSoup(data)
        request_id_cols = soup.find_all('div', class_='panel')
        return len(request_id_cols)

    def test_payout(self):
        self.elevated_list_checker('/request/pay/', 4)

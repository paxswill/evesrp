from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from bs4 import BeautifulSoup
from evesrp import db
from evesrp.models import Request, ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from ...util_tests import TestLogin


def test_empty_personal_listing(srp_request, a_user, user, other_user,
                                get_login):
    assert Request.query.count() == 1
    if a_user == user:
        assert len(a_user.requests) == 1
    else:
        assert len(a_user.requests) == 0
    with get_login(a_user) as client:
        resp = client.get('/request/personal/')
        if a_user == user:
            assert str(srp_request.id) in resp.get_data(as_text=True)
        else:
            assert 'You do not have permission' in resp.get_data(as_text=True)
        # Move the request to other_user
        other_user.requests.append(srp_request)
        db.session.commit()
        resp = client.get('/request/personal/')
        if a_user == user:
            assert 'You have not submitted' in resp.get_data(as_text=True)
        else:
            assert str(srp_request.id) in resp.get_data(as_text=True)


class TestRequestList(TestLogin):

    sample_request_data = {
        'type_name': 'Revenant',
        'type_id': 3514,
        'corporation': 'Center for Advanced Studies',
        'corporation_id': 1000169,
        'kill_timestamp': dt.datetime.utcnow(),
        'system': 'Jita',
        'system_id': 30000142,
        'constellation': 'Kimotoro',
        'constellation_id': 20000020,
        'region': 'The Forge',
        'region_id': 10000002,
        'pilot_id': 1,
    }

    def setUp(self):
        super(TestRequestList, self).setUp()
        with self.app.test_request_context():
            for request in self.get_requests():
                db.session.add(request)
            db.session.commit()

    def get_requests(self):
        """Act as an iterable of requests to add create.

        It is safe to assume this method will be called from within an
        request context.
        """
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
        Pilot(user1, 'Generic Pilot', self.sample_request_data['pilot_id'])
        for division, user in ((d1, user1), (d2, user2)):
            # 2 evaluating, 1 incomplete, 2 approved, 1 rejected,
            # and 1 paid.
            for status in (ActionType.evaluating, ActionType.evaluating,
                           ActionType.incomplete, ActionType.approved,
                           ActionType.approved, ActionType.rejected,
                           ActionType.paid):
                request_details = "User: {}\nDivision: {}\nStatus: {}"\
                        .format(user, division, status)
                yield Request(user, request_details, division,
                        self.sample_request_data.items(),
                        killmail_url='http://paxswill.com',
                        status=status)

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
        soup = BeautifulSoup(data, 'html.parser')
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
        soup = BeautifulSoup(data, 'html.parser')
        request_id_cols = soup.find_all('div', class_='panel')
        return len(request_id_cols)

    def test_payout(self):
        self.elevated_list_checker('/request/pay/', 4)

import re
import datetime as dt
from bs4 import BeautifulSoup
from ..util import TestLogin
from evesrp import db
from evesrp.models import Request, Action, Modifier, ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import User, Pilot, Division, Permission
from evesrp import views
from wtforms.validators import StopValidation, ValidationError


class TestSubmitRequest(TestLogin):

    def setUp(self):
        super(TestSubmitRequest, self).setUp()
        # Setup a bunch of divisions with varying permissions
        with self.app.test_request_context():
            d1 = Division('Division 1')
            d2 = Division('Division 2')
            d3 = Division('Division 3')
            d4 = Division('Division 4')
            d5 = Division('Division 5')
            d6 = Division('Division 6')
            user = self.normal_user
            db.session.add_all((d1, d2, d3, d4, d5, d6))
            # D1: submit, review
            # D2: review
            # D3: submit
            # D4: review, pay
            # D5: pay
            # D6: none
            db.session.add(Permission(d1, PermissionType.submit, user))
            db.session.add(Permission(d1, PermissionType.review, user))
            db.session.add(Permission(d2, PermissionType.review, user))
            db.session.add(Permission(d3, PermissionType.submit, user))
            db.session.add(Permission(d4, PermissionType.review, user))
            db.session.add(Permission(d4, PermissionType.pay, user))
            db.session.add(Permission(d5, PermissionType.pay, user))
            db.session.commit()
        # Python 3 and Python 2.7 have different names for the same method
        try:
            self.assertCountEqual = self.assertItemsEqual
        except AttributeError:
            pass

    def test_division_listing(self):
        client = self.login()
        resp = client.get('/add/')
        matches = re.findall(r'<option.*?>(?P<name>[\w\s]+)</option>',
                resp.get_data(as_text=True))
        self.assertEqual(len(matches), 2)
        self.assertCountEqual(matches, ('Division 1', 'Division 3'))

    def test_submit_divisions(self):
        client = self.login()
        with self.app.test_request_context():
            user = self.normal_user
            divisions = views.requests.submit_divisions(user)
            division_names = [d[1] for d in divisions]
            self.assertEqual(len(division_names), 2)
            self.assertCountEqual(division_names, ('Division 1', 'Division 3'))

    def test_killmail_validation(self):
        # Using a test_client() context so the before_request callbacks are
        # called.
        with self.app.test_client() as c:
            c.get('/add/')
            # RequestsForm needs a list of divisions
            user = self.normal_user
            divisions = views.requests.submit_divisions(user)
            # Tests
            division = Division.query.filter_by(name='Division 1').one()
            zkb_form = views.requests.RequestForm(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True)
            zkb_form.division.choices = divisions
            # Fool InputRequired
            zkb_form.details.raw_data = zkb_form.details.data
            self.assertTrue(zkb_form.validate())
            crest_form = views.requests.RequestForm(
                    url=('http://public-crest.eveonline.com/killmails/'
                         '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'),
                    details='Foo',
                    division=division.id,
                    submit=True)
            crest_form.division.choices = divisions
            crest_form.details.raw_data = crest_form.details.data
            self.assertTrue(crest_form.validate())
            fail_form = views.requests.RequestForm(
                    url='http://google.com',
                    details='Foo',
                    division=division.id,
                    submit=True)
            fail_form.division.choices = divisions
            fail_form.details.raw_data = fail_form.details.data
            self.assertFalse(fail_form.validate())

    def test_submit_killmail(self):
        with self.app.test_request_context():
            user = self.normal_user
            pilot = Pilot(user, 'Paxswill', 570140137)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        resp = client.post('/add/', follow_redirects=True, data=dict(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('38905408', resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(38905408)
            self.assertIsNotNone(request)

    def test_submit_non_personal_killmail(self):
        with self.app.test_request_context():
            user = self.normal_user
            pilot = Pilot(user, 'The Mittani', 443630591)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        resp = client.post('/add/', follow_redirects=True, data=dict(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can only submit killmails of characters you',
                resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(38905408)
            self.assertIsNone(request)


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

    def accessible_list_checker(self, user_name, path, expected):
        client = self.login(user_name)
        resp = client.get(path, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.get_data())
        request_id_cols = soup.find_all('td', class_='col-status')
        self.assertEqual(len(request_id_cols), expected)

    def elevated_list_checker(self, path, expected):
        norm_client = self.login(self.normal_name)
        norm_resp = norm_client.get(path, follow_redirects=True)
        self.assertEqual(norm_resp.status_code, 403)
        self.accessible_list_checker(self.admin_name, path, expected)

    def test_pending(self):
        self.elevated_list_checker('/pending/', 10)

    def test_payout(self):
        self.elevated_list_checker('/pay/', 4)

    def test_complete(self):
        self.elevated_list_checker('/completed/', 4)

    def test_personal(self):
        self.accessible_list_checker(self.normal_name, '/personal/', 7)
        self.accessible_list_checker(self.admin_name, '/personal/', 7)

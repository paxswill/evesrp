import re
import datetime as dt
from decimal import Decimal
from unittest import expectedFailure
from httmock import HTTMock
from bs4 import BeautifulSoup
from ..util import TestLogin, all_mocks
from evesrp import db
from evesrp.models import Request, Action, AbsoluteModifier, RelativeModifier,\
        ActionType, PrettyDecimal
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
        resp = client.get('/request/add/')
        matches = re.findall(r'<option.*?>(?P<name>[\w\s]+)</option>',
                resp.get_data(as_text=True))
        self.assertEqual(len(matches), 2)
        self.assertCountEqual(matches, ('Division 1', 'Division 3'))

    def test_submit_divisions(self):
        client = self.login()
        with self.app.test_request_context():
            user = self.normal_user
            divisions = user.submit_divisions()
            division_names = [d[1] for d in divisions]
            self.assertEqual(len(division_names), 2)
            self.assertCountEqual(division_names, ('Division 1', 'Division 3'))

    def test_killmail_validation(self):
        # Using a test_client() context so the before_request callbacks are
        # called.
        with self.app.test_client() as c:
            c.get('/request/add/')
            # RequestsForm needs a list of divisions
            user = self.normal_user
            divisions = user.submit_divisions()
            # Tests
            # ZKillboard
            division = Division.query.filter_by(name='Division 1').one()
            zkb_form = views.requests.RequestForm(
                    url='https://zkillboard.com/kill/37637533/',
                    details='Foo',
                    division=division.id,
                    submit=True)
            zkb_form.division.choices = divisions
            # Fool InputRequired
            zkb_form.details.raw_data = zkb_form.details.data
            with HTTMock(*all_mocks):
                self.assertTrue(zkb_form.validate())
            # CREST
            crest_form = views.requests.RequestForm(
                    url=('http://public-crest.eveonline.com/killmails/'
                         '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'),
                    details='Foo',
                    division=division.id,
                    submit=True)
            crest_form.division.choices = divisions
            crest_form.details.raw_data = crest_form.details.data
            with HTTMock(*all_mocks):
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
        with HTTMock(*all_mocks):
            resp = client.post('/request/add/', follow_redirects=True,
                    data=dict(
                        url='https://zkillboard.com/kill/37637533/',
                        details='Foo',
                        division=division.id,
                        submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('37637533', resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(37637533)
            self.assertIsNotNone(request)

    def test_submit_non_personal_killmail(self):
        with self.app.test_request_context():
            user = self.normal_user
            pilot = Pilot(user, 'The Mittani', 443630591)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        resp = client.post('/request/add/', follow_redirects=True, data=dict(
                    url='https://zkillboard.com/kill/37637533/',
                    details='Foo',
                    division=division.id,
                    submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can only submit killmails of characters you',
                resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(37637533)
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
        self.elevated_list_checker('/request/pending/', 10)

    def test_payout(self):
        self.elevated_list_checker('/request/pay/', 4)

    def test_complete(self):
        self.elevated_list_checker('/request/completed/', 4)

    def test_personal(self):
        self.accessible_list_checker(self.normal_name, '/request/personal/', 7)
        self.accessible_list_checker(self.admin_name, '/request/personal/', 7)


class TestRequest(TestLogin):

    def setUp(self):
        super(TestRequest, self).setUp()
        with self.app.test_request_context():
            d1 = Division('Division One')
            d2 = Division('Division Two')
            db.session.add(d1)
            db.session.add(d2)
            # Yup, the Gyrobus killmail
            mock_killmail = dict(
                    id=12842852,
                    ship_type='Erebus',
                    corporation='Ever Flow',
                    alliance='Northern Coalition.',
                    killmail_url=('http://eve-kill.net/?a=kill_detail'
                        '&kll_id=12842852'),
                    base_payout=73957900000,
                    kill_timestamp=dt.datetime(2012, 3, 25, 0, 44, 0,
                        tzinfo=dt.timezone.utc),
                    system='92D-OI',
                    constellation='XHYS-O',
                    region='Venal',
                    pilot_id=133741,
            )
            Pilot(self.normal_user, 'eLusi0n', 133741)
            Request(self.normal_user, 'Original details', d1,
                    mock_killmail.items())
            db.session.commit()
        self.request_path = '/request/12842852/'

    def _add_permission(self, user_name, permission,
            division_name='Division One'):
        """Helper to grant permissions to the division the request is in."""
        with self.app.test_request_context():
            division = Division.query.filter_by(name=division_name).one()
            user = User.query.filter_by(name=user_name).one()
            Permission(division, permission, user)
            db.session.commit()

    @property
    def request(self):
        return Request.query.get(12842852)

class TestRequestAccess(TestRequest):

    def test_basic_request_access(self):
        # Grab some clients
        # The normal user is the submitter
        norm_client = self.login(self.normal_name)
        admin_client = self.login(self.admin_name)
        # Users always have access to requests they've submitted
        resp = norm_client.get(self.request_path)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Lossmail', resp.get_data(as_text=True))
        resp = admin_client.get(self.request_path)
        self.assertEqual(resp.status_code, 403)

    def _test_permission_access(self, user_name, permission,
            division_name, accessible=True):
        self._add_permission(user_name, permission, division_name)
        # Get a client and fire off the request
        client = self.login(user_name)
        resp = client.get(self.request_path)
        if accessible:
            self.assertEqual(resp.status_code, 200)
            self.assertIn('Lossmail', resp.get_data(as_text=True))
        else:
            self.assertEqual(resp.status_code, 403)

    def test_review_same_division_access(self):
        self._test_permission_access(self.admin_name, PermissionType.review,
                'Division One')

    def test_review_other_division_access(self):
        self._test_permission_access(self.admin_name, PermissionType.review,
                'Division Two', False)

    def test_pay_same_division_access(self):
        self._test_permission_access(self.admin_name, PermissionType.pay,
                'Division One')

    def test_pay_other_division_access(self):
        self._test_permission_access(self.admin_name, PermissionType.pay,
                'Division Two', False)


class TestRequestSetPayout(TestRequest):

    def _test_set_payout(self, user_name, permission, permissable=True):
        if permission is not None:
            self._add_permission(user_name, permission)
        client = self.login(user_name)
        test_payout = 42
        with client as c:
            resp = client.post(self.request_path, follow_redirects=True, data={
                    'id_': 'payout',
                    'value': test_payout})
            self.assertEqual(resp.status_code, 200)
            with self.app.test_request_context():
                payout = self.request.payout
                base_payout = self.request.base_payout
            if permissable:
                real_test_payout = test_payout * 1000000
                self.assertIn(PrettyDecimal(real_test_payout).currency(),
                        resp.get_data(as_text=True))
                self.assertEqual(payout, real_test_payout)
            else:
                self.assertIn('Only reviewers can change the base payout.',
                        resp.get_data(as_text=True))
                self.assertEqual(base_payout, Decimal('73957900000'))

    def test_reviewer_set_base_payout(self):
        self._test_set_payout(self.admin_name, PermissionType.review)

    def test_payer_set_base_payout(self):
        self._test_set_payout(self.admin_name, PermissionType.pay, False)

    def test_submitter_set_base_payout(self):
        self._test_set_payout(self.normal_name, None, False)

    def test_set_payout_invalid_request_state(self):
        statuses = (
            ActionType.approved,
            ActionType.paid,
            ActionType.rejected,
            ActionType.incomplete,
        )
        self._add_permission(self.normal_name, PermissionType.review)
        self._add_permission(self.normal_name, PermissionType.pay)
        client = self.login()
        for status in statuses:
            with self.app.test_request_context():
                if status == ActionType.paid:
                    self.request.status = ActionType.approved
                self.request.status = status
                db.session.commit()
            resp = client.post(self.request_path, follow_redirects=True, data={
                    'id_': 'payout',
                    'value': '42000000'})
            self.assertIn('The request must be in the evaluating state '
                    'to change the base payout.', resp.get_data(as_text=True))
            with self.app.test_request_context():
                self.request.status = ActionType.evaluating
                db.session.commit()


class TestRequestAddModifiers(TestRequest):

    def _test_add_modifier(self, user_name, permissible=True):
        client = self.login(user_name)
        resp = client.post(self.request_path, follow_redirects=True, data={
                'id_': 'modifier',
                'value': '10',
                'type_': 'abs-bonus',})
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            modifiers = self.request.modifiers.all()
            modifiers_length = len(modifiers)
            if modifiers_length > 0:
                first_value = modifiers[0].value
        if permissible:
            self.assertEqual(modifiers_length, 1)
            self.assertEqual(first_value, 10000000)
        else:
            self.assertEqual(modifiers_length, 0)
            self.assertIn('Only reviewers can add modifiers.',
                    resp.get_data(as_text=True))

    def test_reviewer_add_modifier(self):
        self._add_permission(self.admin_name, PermissionType.review)
        self._test_add_modifier(self.admin_name)

    def test_payer_add_modifier(self):
        self._add_permission(self.admin_name, PermissionType.pay)
        self._test_add_modifier(self.admin_name, False)

    def test_submitter_add_modifier(self):
        self._test_add_modifier(self.normal_name, False)


class TestRequestVoidModifiers(TestRequest):

    def _add_modifier(self, user_name, value, absolute=True):
        with self.app.test_request_context():
            user = User.query.filter_by(name=user_name).one()
            if absolute:
                mod = AbsoluteModifier(self.request, user, '', value)
            else:
                mod = RelativeModifier(self.request, user, '', value)
            db.session.commit()
            return mod.id

    def _test_void_modifier(self, user_name, permissible=True):
        self._add_permission(self.admin_name, PermissionType.review)
        mod_id = self._add_modifier(self.admin_name, 10)
        client = self.login(user_name)
        resp = client.post(self.request_path, follow_redirects=True, data={
                'id_': 'void',
                'modifier_id': mod_id})
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            payout = self.request.payout
        if permissible:
            self.assertEqual(payout, Decimal(73957900000))
        else:
            self.assertEqual(payout, Decimal(73957900000) + 10)
            self.assertIn('You must be a reviewer to be able to void',
                    resp.get_data(as_text=True))

    def test_reviewer_void_modifier(self):
        self._add_permission(self.normal_name, PermissionType.review)
        self._test_void_modifier(self.normal_name)

    def test_payer_void_modifier(self):
        self._add_permission(self.normal_name, PermissionType.pay)
        self._test_void_modifier(self.normal_name, False)

    def test_submitter_void_modifier(self):
        self._test_void_modifier(self.normal_name, False)

    @expectedFailure
    def test_modifier_evaluation(self):
        with self.app.test_request_context():
            self.assertEqual(int(self.request.payout), 73957900000)
            Modifier(self.request, self.normal_user, 'Details',
                    type_='absolute', value=10)
            db.session.commit()
            self.assertEqual(int(self.request.payout), 73957900000 + 10000000)
            Modifier(self.request, self.normal_user, '', type_='absolute',
                    value=(-10))
            db.session.commit()
            self.assertEqual(int(self.request.payout), 73957900000)

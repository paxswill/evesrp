from __future__ import absolute_import
from __future__ import unicode_literals
import re
import datetime as dt
from decimal import Decimal
from ...util import TestLogin
from evesrp import db
from evesrp.models import Request, Action, AbsoluteModifier, RelativeModifier,\
        ActionType, PrettyDecimal
from evesrp.auth import PermissionType
from evesrp.auth.models import User, Pilot, Division, Permission
from evesrp.util import utc
from evesrp import views


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
                        tzinfo=utc),
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
                    'value': '42'})
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

    def test_modifier_evaluation(self):
        with self.app.test_request_context():
            self._add_permission(self.admin_name, PermissionType.review)
            self.assertEqual(self.request.payout, Decimal(73957900000))
            self._add_modifier(self.admin_name, Decimal(10000000))
            self.assertEqual(self.request.payout,
                    Decimal(73957900000) + Decimal(10000000))
            self._add_modifier(self.admin_name, Decimal('-0.1'), False)
            self.assertEqual(self.request.payout,
                    (Decimal(73957900000) + Decimal(10000000)) *
                    (1 + Decimal('-0.1')))


class TestChangeDivision(TestRequest):

    def setUp(self):
        super(TestChangeDivision, self).setUp()
        with self.app.test_request_context():
            db.session.add(Division('Division Three'))
            db.session.commit()

    def _send_request(self, user_name):
        with self.app.test_request_context():
            new_division_id = Division.query.filter_by(
                    name='Division Two').one().id
        client = self.login(user_name)
        return client.post(self.request_path + 'division/',
                follow_redirects=True,
                data={'division': new_division_id})

    def test_submitter_change_submit_division(self):
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Two')
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Three')
        resp = self._send_request(self.normal_name)
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            d2 = Division.query.filter_by(name='Division Two').one()
            self.assertEqual(self.request.division, d2)

    def test_submitter_change_nonsubmit_division(self):
        resp = self._send_request(self.normal_name)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(u"No other divisions", resp.get_data(as_text=True))
        with self.app.test_request_context():
            d1 = Division.query.filter_by(name='Division One').one()
            self.assertEqual(self.request.division, d1)

    def test_submitter_change_division_finalized(self):
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Two')
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Three')
        self._add_permission(self.admin_name, PermissionType.admin)
        with self.app.test_request_context():
            Action(self.request, self.admin_user, type_=ActionType.rejected)
            db.session.commit()
        resp = self._send_request(self.normal_name)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(u"in a finalized state", resp.get_data(as_text=True))
        with self.app.test_request_context():
            d1 = Division.query.filter_by(name='Division One').one()
            self.assertEqual(self.request.division, d1)

    def test_reviewer_change_division(self):
        self._add_permission(self.admin_name, PermissionType.review)
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Two')
        self._add_permission(self.normal_name, PermissionType.submit,
                'Division Three')
        resp = self._send_request(self.normal_name)
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            d2 = Division.query.filter_by(name='Division Two').one()
            self.assertEqual(self.request.division, d2)

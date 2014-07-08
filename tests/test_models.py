from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from .util import TestLogin
from evesrp import db
from evesrp.models import ActionType, ActionError, Action, Request,\
        AbsoluteModifier, RelativeModifier, ModifierError
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp.util.utc import utc


class TestModels(TestLogin):

    def setUp(self):
        super(TestModels, self).setUp()
        with self.app.test_request_context():
            div = Division('Testing Division')
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
            Request(self.normal_user, 'Original details', div,
                    mock_killmail.items())
            Permission(div, PermissionType.review, self.admin_user)
            Permission(div, PermissionType.pay, self.admin_user)
            db.session.commit()

    @property
    def request(self):
        return Request.query.first()

    def add_action(self, type_):
        Action(self.request, self.admin_user, type_=type_)
        db.session.commit()


class TestModifiers(TestModels):

    def test_add_modifier(self):
        with self.app.test_request_context():
            start_payout = float(self.request.payout)
            AbsoluteModifier(self.request, self.admin_user, '', 10)
            db.session.commit()
            self.assertEqual(float(self.request.payout), start_payout + 10)
        return start_payout

    def test_void_modifier(self):
        start_payout = self.test_add_modifier()
        with self.app.test_request_context():
            mod = self.request.modifiers[0].void(self.admin_user)
            db.session.commit()
            self.assertEqual(float(self.request.payout), start_payout)

    def test_add_modifier_bad_status(self):
        with self.app.test_request_context():
            self.add_action(ActionType.approved)
            with self.assertRaises(ModifierError):
                AbsoluteModifier(self.request, self.admin_user, '', 10)
                db.session.commit()

    def test_void_modifier_bad_status(self):
        start_payout = self.test_add_modifier()
        with self.app.test_request_context():
            self.add_action(ActionType.approved)
            mod = self.request.modifiers[0]
            with self.assertRaises(ModifierError):
                mod.void(self.admin_user)
                db.session.commit()
            self.assertNotEqual(float(self.request.payout), start_payout)

    def test_add_modifier_bad_permissions(self):
        with self.app.test_request_context():
            with self.assertRaises(ModifierError):
                AbsoluteModifier(self.request, self.normal_user, '', 10)
                db.session.commit()

    def test_void_modifier_bad_permissions(self):
        start_payout = self.test_add_modifier()
        with self.app.test_request_context():
            mod = self.request.modifiers[0]
            with self.assertRaises(ModifierError):
                mod.void(self.normal_user)
                db.session.commit()
            self.assertNotEqual(float(self.request.payout), start_payout)


class TestActionStatus(TestModels):

    def test_default_status(self):
        with self.app.test_request_context():
            # Check default status
            self.assertEqual(self.request.status, ActionType.evaluating)

    def test_status_updating(self):
        with self.app.test_request_context():
            Action(self.request, self.admin_user, type_=ActionType.approved)
            db.session.commit()
            self.assertEqual(self.request.status, ActionType.approved)

    def test_status_state_machine(self):
        with self.app.test_request_context():
            # To and From evaluating (except from paid)
            for action in (ActionType.incomplete, ActionType.rejected,
                    ActionType.approved):
                self.add_action(action)
                self.assertEqual(self.request.status, action)
                self.add_action(ActionType.evaluating)
                self.assertEqual(self.request.status, ActionType.evaluating)
            with self.assertRaises(ActionError):
                self.add_action(ActionType.paid)
            # From incomplete
            self.add_action(ActionType.incomplete)
            self.add_action(ActionType.rejected)
            self.assertEqual(self.request.status, ActionType.rejected)
            # From rejected
            for action in ActionType.statuses.difference(
                    (ActionType.evaluating,)):
                with self.assertRaises(ActionError):
                    self.add_action(action)
            self.add_action(ActionType.evaluating)
            # From approved
            self.add_action(ActionType.approved)
            for action in (ActionType.incomplete, ActionType.rejected):
                with self.assertRaises(ActionError):
                    self.add_action(action)
            self.add_action(ActionType.paid)
            self.assertEqual(self.request.status, ActionType.paid)
            # From paid
            for action in (ActionType.incomplete, ActionType.rejected):
                with self.assertRaises(ActionError):
                    self.add_action(action)
            self.add_action(ActionType.approved)
            self.assertEqual(self.request.status, ActionType.approved)
            self.add_action(ActionType.paid)
            self.add_action(ActionType.evaluating)
            self.assertEqual(self.request.status, ActionType.evaluating)

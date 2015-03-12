from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from decimal import Decimal
from .util_tests import TestLogin
from evesrp import db
from evesrp.models import ActionType, ActionError, Action, Request,\
        Modifier, AbsoluteModifier, RelativeModifier, ModifierError
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp.util import utc


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
                    base_payout=Decimal(73957900000),
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
        action = Action(self.request, self.admin_user, type_=type_)
        db.session.commit()
        return action.id

    def add_modifier(self, value, absolute=True):
        if absolute:
            modifier = AbsoluteModifier(self.request, self.admin_user, None,
                    Decimal(value))
        else:
            modifier = RelativeModifier(self.request, self.admin_user, None,
                    Decimal(value))
        db.session.add(modifier)
        db.session.commit()
        return modifier.id


class TestModifiers(TestModels):

    def test_add_modifier(self):
        with self.app.test_request_context():
            start_payout = self.request.payout
            AbsoluteModifier(self.request, self.admin_user, '', 10)
            db.session.commit()
            self.assertEqual(self.request.payout, start_payout + 10)
        return start_payout

    def test_void_modifier(self):
        start_payout = self.test_add_modifier()
        with self.app.test_request_context():
            mod = self.request.modifiers[0].void(self.admin_user)
            db.session.commit()
            self.assertEqual(self.request.payout, start_payout)

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
            self.assertNotEqual(self.request.payout, start_payout)

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
            self.assertNotEqual(self.request.payout, start_payout)


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


class TestDelete(TestModels):

    def test_delete_action(self):
        with self.app.test_request_context():
            aid = self.add_action(ActionType.approved)
            db.session.delete(Action.query.get(aid))
            db.session.commit()
            self.assertIsNotNone(self.request)

    def test_delete_modifier(self):
        with self.app.test_request_context():
            mid = self.add_modifier(10)
            db.session.delete(Modifier.query.get(mid))
            db.session.commit()
            self.assertIsNotNone(self.request)

    def test_delete_request(self):
        with self.app.test_request_context():
            rid = self.request.id
            mid = self.add_modifier(10)
            aid = self.add_action(ActionType.approved)
            db.session.delete(self.request)
            db.session.commit()
            self.assertIsNone(Modifier.query.get(mid))
            self.assertIsNone(Action.query.get(aid))
            self.assertIsNone(self.request)

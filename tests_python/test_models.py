from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from decimal import Decimal
import pytest
from .util_tests import TestLogin
from evesrp import db
from evesrp.models import ActionType, ActionError, Action, Request,\
        Modifier, AbsoluteModifier, RelativeModifier, ModifierError
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp.util import utc


pytestmark = pytest.mark.usefixtures('request_context')


@pytest.fixture(params=ActionType.statuses, ids=(lambda s: s.value))
def request_status(request, srp_request, other_user):
    # Skip if the status already matches
    if request.param == srp_request.status:
        return request.param
    # For paid status, we need to be approved first
    if request.param == ActionType.paid:
        Action(srp_request, other_user, type_=ActionType.approved)
    Action(srp_request, other_user, type_=request.param)
    db.session.commit()
    assert srp_request.status == request.param
    return request.param


# Just a way to test success and failure of permissions
@pytest.fixture(params=[True, False], ids=['user', 'other_user'])
def a_user(request, user, other_user):
    if request.param:
        return user
    else:
        return other_user


class TestModifiers(object):

    def test_add_modifier(self, srp_request, a_user, request_status):
        status_success = request_status == ActionType.evaluating
        permissions_success = 'Other' in a_user.name
        start_payout = srp_request.payout
        if status_success and permissions_success:
            AbsoluteModifier(srp_request, a_user, '', 10)
            db.session.commit()
            assert srp_request.payout == start_payout + 10
        else:
            with pytest.raises(ModifierError) as excinfo:
                AbsoluteModifier(srp_request, a_user, '', 10)
                db.session.commit()

    def test_void_modifier(self, srp_request, a_user, request_status):
        status_success = request_status == ActionType.evaluating
        permissions_success = 'Other' in a_user.name
        start_payout = srp_request.payout
        modifier = srp_request.modifiers[0]
        if status_success and permissions_success:
            modifier.void(a_user)
            db.session.commit()
            assert srp_request.payout == srp_request.base_payout
        else:
            with pytest.raises(ModifierError) as excinfo:
                modifier.void(a_user)
                db.session.commit()


class TestActionStatus(object):

    def test_default_status(self, srp_request):
        assert srp_request.status == ActionType.evaluating

    @pytest.fixture(params=ActionType.statuses, ids=(lambda s: s.value))
    def next_status(self, request):
        return request.param

    # Also implicitly testing the setting of Request.status
    def test_state_machine(self, srp_request, other_user, request_status,
                           next_status):
        success = next_status in Request.state_rules[request_status]
        if success:
            Action(srp_request, other_user, type_=next_status)
            db.session.commit()
            assert srp_request.status == next_status
        else:
            with pytest.raises(ActionError) as excinfo:
                Action(srp_request, other_user, type_=next_status)
                db.session.commit()
            assert srp_request.status == request_status


class TestDelete(object):

    def test_delete_action(self, srp_request, other_user):
        action = Action(srp_request, other_user, type_=ActionType.approved)
        db.session.commit()
        db.session.delete(action)
        db.session.commit()
        db.session.expire_all()
        assert srp_request is not None

    def test_delete_modifier(self, srp_request):
        modifier = srp_request.modifiers[0]
        db.session.delete(modifier)
        db.session.commit()
        db.session.expire_all()
        assert srp_request is not None

    def test_delete_request(self, srp_request, other_user):
        action = Action(srp_request, other_user, type_=ActionType.approved)
        modifier = srp_request.modifiers[0]
        db.session.commit()
        action_id = action.id
        modifier_id = modifier.id
        request_id = srp_request.id
        db.session.delete(srp_request)
        db.session.commit()
        db.session.expire_all()
        assert AbsoluteModifier.query.get(modifier_id) is None
        assert Action.query.get(action_id) is None
        assert Request.query.get(request_id) is None

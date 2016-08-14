from __future__ import absolute_import
import pytest
from evesrp import db
from evesrp.models import ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import Division, Permission


pytestmark = pytest.mark.parametrize('user_role', ('Normal', ))


@pytest.fixture
def srp_request(srp_request):
    division = srp_request.division
    permissions = Permission.query.filter_by(division=division).delete()
    db.session.commit()
    return srp_request


@pytest.fixture
def request_path(srp_request):
    return '/request/{}/'.format(srp_request.id)


@pytest.fixture
def other_division(evesrp_app):
    division = Division('Other Division')
    db.session.commit()
    return division


@pytest.fixture(params=(PermissionType.review, PermissionType.pay,
                        PermissionType.submit), ids=(lambda p: p.value))
def permission(request):
    return request.param


@pytest.fixture(params=(ActionType.approved, ActionType.paid,
                        ActionType.rejected, ActionType.incomplete),
                ids=(lambda s: s.value))
def status(request):
    return request.param


def test_basic_request_access(user, other_user, get_login, request_path):
    # Test that the owning user has access, and other users do not
    other_resp = get_login(other_user).get(request_path)
    assert other_resp.status_code == 403
    owner_resp = get_login(user).get(request_path)
    assert owner_resp.status_code == 200
    assert 'Lossmail' in owner_resp.get_data(as_text=True)


@pytest.mark.parametrize('permission', (PermissionType.review,
                                        PermissionType.pay),
                         ids=(lambda p: p.value))
@pytest.mark.parametrize('division_name', ('Testing Division',
                                           'Other Division'))
def test_permission_access(other_user, get_login, permission,
                           division_name, other_division, srp_request,
                           request_path):
    # Test that users with the appropriate permission in the appropriate
    # division have access to the request
    if division_name == 'Testing Division':
        division = srp_request.division
    else:
        division = other_division
    Permission(division, permission, other_user)
    db.session.commit()
    resp = get_login(other_user).get(request_path)
    if division_name == 'Testing Division':
        assert resp.status_code == 200
        assert 'Lossmail' in resp.get_data(as_text=True)
    else:
        assert resp.status_code == 403


def test_set_payout(user, other_user, get_login, permission, srp_request,
                    request_path):
    if permission != PermissionType.submit:
        # This could be confusing, but for the cases where you're testing
        # that users other than the submitter can access the request with
        # the correct permission we set 'user' to the value of 'other_user'
        # just so it's a bit easier to type out.
        user = other_user
        Permission(srp_request.division, permission, user)
    test_payout = 42
    old_payout = srp_request.base_payout
    with get_login(user) as client:
        resp = client.post(request_path, follow_redirects=True, data={
                'id_': 'payout',
                'value': test_payout})
        payout = srp_request.base_payout
        # When submitting, the value is in millions. Scale it back when we
        # compare it to the request's base payout.
        test_payout *= 1000000
        # Check that the correct status code gets returned and that the
        # payout didn't change
        if permission == PermissionType.review:
            assert resp.status_code == 200
            assert payout == test_payout
        else:
            assert resp.status_code == 403
            assert payout == old_payout


def test_set_payout_invalid_state(user, get_login, srp_request, request_path,
                                  status):
    if status == ActionType.paid:
        # Satisfy the state machine
        srp_request.status = ActionType.approved
    srp_request.status = status
    # Add permissions so this user can change the payout
    Permission(srp_request.division, PermissionType.review, user)
    db.session.commit()
    before_payout = srp_request.base_payout
    with get_login(user) as client:
        resp = client.post(request_path, follow_redirects=True,
                           data={
                               'id_': 'payout',
                               'value': '42',
                           })
        assert resp.status_code == 400
        assert srp_request.base_payout == before_payout


def test_add_modifier(user, other_user, get_login, srp_request, request_path,
                      permission):
    if permission != PermissionType.submit:
        user = other_user
        Permission(srp_request.division, permission, user)
        db.session.commit()
    before_modifier_count = len(srp_request.modifiers.all())
    with get_login(user) as client:
        resp = client.post(request_path, follow_redirects=True,
                           data={
                               'id_': 'modifier',
                               'value': '10',
                               'type_': 'abs-bonus',
                           })
        modifier_count = len(srp_request.modifiers.all())
        if permission == PermissionType.review:
            assert resp.status_code == 200
            assert (before_modifier_count + 1) == modifier_count
        else:
            assert resp.status_code == 403
            assert before_modifier_count == modifier_count


def test_add_modifier_invalid_state(user, get_login, srp_request, request_path,
                                    status):
    if status == ActionType.paid:
        srp_request.status = ActionType.approved
    srp_request.status = status
    Permission(srp_request.division, PermissionType.review, user)
    db.session.commit()
    before_modifier_count = len(srp_request.modifiers.all())
    with get_login(user) as client:
        resp = client.post(request_path, follow_redirects=True,
                           data={
                               'id_': 'modifier',
                               'value': '10',
                               'type_': 'abs-bonus',
                           })
        modifier_count = len(srp_request.modifiers.all())
        assert resp.status_code == 400
        assert modifier_count == before_modifier_count


def test_void_modifier(user, other_user, get_login, srp_request, request_path,
                       permission):
    if permission != PermissionType.submit:
        user = other_user
        Permission(srp_request.division, permission, user)
        db.session.commit()
    before_payout = srp_request.payout
    mod_id = srp_request.modifiers.one().id
    with get_login(user) as client:
        resp = client.post(request_path, follow_redirects=True,
                           data={
                               'id_': 'void',
                               'modifier_id': mod_id,
                           })
        if permission == PermissionType.review:
            assert resp.status_code == 200
            assert srp_request.payout != before_payout
        else:
            assert resp.status_code == 403
            assert srp_request.payout == before_payout


@pytest.mark.parametrize('new_division', (True, False),
                         ids=('New_Division', 'No_New_Division'))
@pytest.mark.parametrize('status', ActionType.statuses,
                         ids=(lambda s: s.value))
def test_change_division(user, other_user, get_login, srp_request,
                         request_path, permission, status, new_division):
    # Set up the new division and permissions
    other_division = Division("Other Division")
    if permission != PermissionType.submit:
        user = other_user
        Permission(srp_request.division, permission, user)
    if new_division:
        Permission(other_division, PermissionType.submit,
                   srp_request.submitter)
    # Massage the request status if needed
    if status != ActionType.evaluating:
        if status == ActionType.paid:
            srp_request.status = ActionType.approved
        srp_request.status = status
    db.session.commit()
    old_division_id = srp_request.division.id
    with get_login(user) as client:
        resp = client.post(request_path + 'division/', follow_redirects=True,
                           data={'division': other_division.id})
        # PermissionType.pay is the only permission under test here that can't
        # change the division.
        if permission == PermissionType.pay:
            assert resp.status_code == 403
            success = False
        elif status not in ActionType.pending:
            assert 'finalized state' in resp.get_data(as_text=True)
            # redirect causing an eventual 200
            assert resp.status_code == 200
            success = False
        elif not new_division:
            assert 'No other divisions' in resp.get_data(as_text=True)
            # redirect ahoy
            assert resp.status_code == 200
            success = False
        else:
            assert 'moved to' in resp.get_data(as_text=True)
            success = True
        assert (old_division_id != srp_request.division.id) == success

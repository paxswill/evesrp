try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from evesrp.users import request, errors
from evesrp import new_models as models


@pytest.mark.parametrize('use_user_id', (True, False))
def test_submitter_init(use_user_id):
    store = mock.Mock()
    user = mock.Mock()
    user.id_ = 5
    store.get_user.return_value = user
    if use_user_id:
        submitter = request.RequestSubmissionActivity(store, user.id_)
    else:
        submitter = request.RequestSubmissionActivity(store, user)
    assert submitter.store == store
    assert submitter.user == user
    if use_user_id:
        store.get_user.assert_called_with(user_id=user.id_)


@pytest.fixture
def submit_division():
    division = mock.Mock(id_=3)
    return division


@pytest.fixture
def submit_user():
    user = mock.Mock()
    user.id_ = 1
    # Both submit and audit are required to test a conditional in a set
    # comprehension in RequestSubmissionActivity.list_divisions
    user.get_permissions.return_value = [
        mock.Mock(division_id=3, type_=models.PermissionType.submit),
        mock.Mock(division_id=2, type_=models.PermissionType.audit),
    ]
    return user


@pytest.fixture
def submit_store(submit_division):
    store = mock.Mock()
    store.get_divisions.return_value = [submit_division]
    return store


def test_submitter_list_divisions(submit_user, submit_store, submit_division):
    submitter = request.RequestSubmissionActivity(submit_store, submit_user)
    assert submitter.list_divisions() == [submit_division]
    submit_store.get_divisions.assert_called_with(
        division_ids={submit_division.id_})
    submit_user.get_permissions.assert_called_with(submit_store)


@pytest.mark.parametrize('use_division_id', (True, False))
@pytest.mark.parametrize('use_killmail_id', (True, False))
def test_submitter_submit(use_division_id, use_killmail_id, submit_user,
                          submit_store, submit_division):
    permission = mock.Mock()
    submit_store.get_permission.return_value = [permission]
    killmail = mock.Mock()
    killmail.id_ = 4
    if use_division_id:
        test_division = submit_division.id_
        submit_store.get_division.return_value = submit_division
    else:
        test_division = submit_division
    if use_killmail_id:
        test_killmail = killmail.id_
        submit_store.get_killmail.return_value = killmail
    else:
        test_killmail = killmail
    submitter = request.RequestSubmissionActivity(submit_store, submit_user)
    submitted_request = submitter.submit_request("Detailed details.",
                                                 test_division,
                                                 test_killmail)
    assert submitted_request.details == "Detailed details."
    assert submitted_request.killmail_id == killmail.id_
    assert submitted_request.division_id == submit_division.id_
    submit_store.add_request.assert_called_with(submitted_request)
    if use_division_id:
        submit_store.get_division.assert_called_with(
            division_id=submit_division.id_)
    if use_killmail_id:
        submit_store.get_killmail.assert_called_with(killmail_id=killmail.id_)


OWNER_ID = 23
DIVISION_ID = 49


@pytest.fixture
def killmail(killmail_data):
    killmail_splat = dict(killmail_data)
    killmail_splat = dict(killmail_data)
    killmail_splat['id_'] = killmail_data['id']
    killmail_splat['user_id'] = OWNER_ID
    killmail = mock.create_autospec(models.Killmail, **killmail_splat)
    return killmail


@pytest.fixture
def srp_request(killmail):
    request_splat = {
        'id_': 74,
        'details': "Some details about a loss.",
        'killmail_id': killmail.user_id,
        'division_id': DIVISION_ID,
    }
    srp_request = mock.create_autospec(models.Request, **request_splat)
    srp_request.get_killmail.return_value = killmail
    return srp_request


@pytest.fixture
def request_store(srp_request, killmail):
    store = mock.Mock()
    store.get_request.return_value = srp_request
    store.get_killmail.return_value = killmail
    return store


@pytest.fixture(params=models.PermissionType)
def permission(request):
    return request.param


# TODO: Add test for a user having that permission in another division
@pytest.mark.parametrize('user_id', (OWNER_ID, 2))
def test_request_init(permission, request_store, srp_request, user_id):
    user = mock.Mock(id_=user_id)
    user.get_permissions.return_value = {
        # Using division #1
        (permission, DIVISION_ID),
        ('user_id', user_id),
    }
    PT = models.PermissionType
    # User ID $OWNER_ID is the owner, user ID 2 is someone else
    if permission in PT.elevated or \
            (permission == PT.submit and \
             request_store.get_killmail(request_store).user_id == user.id_):
        activity = request.RequestActivity(request_store, user,
                                           request=srp_request.id_)
        assert activity is not None
        assert activity.store == request_store
        assert activity.user == user
    else:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity = request.RequestActivity(request_store, user,
                                               request=srp_request.id_)


@pytest.fixture
def allowed_permissions(srp_request):
    allowed = {(pt, srp_request.division_id) for pt in
               models.PermissionType.elevated}
    allowed.add(('user_id', 1))
    return allowed


@pytest.fixture(params=(
    (models.PermissionType.review, DIVISION_ID),
    (models.PermissionType.admin, DIVISION_ID),
    (models.PermissionType.audit, DIVISION_ID),
    (models.PermissionType.pay, DIVISION_ID),
    ('user_id', OWNER_ID),
))
def permission_tuple(request):
    return request.param


@pytest.fixture
def permission_user(permission_tuple):
    if permission_tuple[0] == 'user_id':
        user = mock.Mock(id_=OWNER_ID)
        user.get_permissions.return_value = {
            permission_tuple,
        }
    else:
        user = mock.Mock(id_=22)
        user.get_permissions.return_value = {
            permission_tuple,
            ('user_id', 22),
        }
    return user


def test_add_comment(request_store, srp_request, permission_tuple,
                     permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    # Out of the elevated privileges, only auditors are unable to comment.
    comment_text = "Oh, hey. A comment."
    if permission_tuple[0] == models.PermissionType.audit:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.comment(comment_text)
    else:
        action = activity.comment(comment_text)
        action_type = models.ActionType.comment
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


@pytest.mark.parametrize('starting_status', (
    models.ActionType.evaluating,
    models.ActionType.paid,
))
def test_mark_approved(request_store, srp_request, permission_tuple,
                       permission_user, starting_status):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    srp_request.status = starting_status
    comment_text = "A comment about an approval."
    # Only Reviewers and Admins can approve if the request is from evaluating
    if starting_status == models.ActionType.evaluating:
        allowed_permissions = (models.PermissionType.review,
                               models.PermissionType.admin)
    # If the request is coming from a paid state, only admins and payers can do
    # that.
    else:
        allowed_permissions = (models.PermissionType.pay,
                               models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.approve(comment_text)
    else:
        action = activity.approve(comment_text)
        action_type = models.ActionType.approved
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


def test_mark_incomplete(request_store, srp_request, permission_tuple,
                         permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    # Only reviewers and admins can incomplete
    comment_text = "This request is bad. Think about what you did."
    allowed_permissions = (models.PermissionType.review,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.incomplete(comment_text)
    else:
        action = activity.incomplete(comment_text)
        action_type = models.ActionType.incomplete
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


@pytest.mark.parametrize('starting_status', (
    models.ActionType.approved,
    models.ActionType.rejected,
    models.ActionType.incomplete,
    models.ActionType.paid,
))
def test_mark_evaluating(request_store, srp_request, permission_tuple,
                         permission_user, starting_status):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    srp_request.status = starting_status
    comment_text = "On second thought, let's think about this some more."
    # Reviewers (and Admins) are able to send a Request back to evaluating from
    # any state except for from paid. Only Payers (and Admins) are able to do
    # that. In addition, the submitter can set a request back to evaluating
    # from the incomplete state by editing the details but that is tested
    # elsewhere.
    if starting_status == models.ActionType.paid:
        allowed_permissions = (models.PermissionType.pay,
                               models.PermissionType.admin)
    else:
        allowed_permissions = (models.PermissionType.review,
                               models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.evaluate(comment_text)
    else:
        action = activity.evaluate(comment_text)
        action_type = models.ActionType.evaluating
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


def test_mark_paid(request_store, srp_request, permission_tuple,
                   permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    # Only Payers (and Admins) can mark a request as paid.
    comment_text = "Done and done."
    allowed_permissions = (models.PermissionType.pay,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.pay(comment_text)
    else:
        action = activity.pay(comment_text)
        action_type = models.ActionType.paid
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


def test_mark_rejected(request_store, srp_request, permission_tuple,
                       permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    # Only Reviewers (and Admins, as usual) can reject requests.
    comment_text = "No ISK for you!"
    allowed_permissions = (models.PermissionType.review,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.reject(comment_text)
    else:
        action = activity.reject(comment_text)
        action_type = models.ActionType.rejected
        srp_request.add_action.assert_called_once_with(request_store,
                                                       action_type,
                                                       contents=comment_text,
                                                       user=permission_user)


@pytest.mark.parametrize('modifier_type', models.ModifierType)
def test_add_modifier(request_store, srp_request, permission_tuple,
                      permission_user, modifier_type):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    if modifier_type == models.ModifierType.relative:
        add_modifier = activity.add_relative_modifier
    elif modifier_type == models.ModifierType.absolute:
        add_modifier = activity.add_absolute_modifier
    # Only reviewers and admins are able to add modifiers
    allowed_permissions = (models.PermissionType.review,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            add_modifier(mock.sentinel.modifier_value,
                         mock.sentinel.modifier_note)
    else:
        add_modifier(mock.sentinel.modifier_value, mock.sentinel.modifier_note)
        modifier_mock = srp_request.add_modifier
        modifier_mock.assert_called_once_with(request_store,
                                              modifier_type,
                                              mock.sentinel.modifier_value,
                                              note=mock.sentinel.modifier_note,
                                              user=permission_user)


def test_void_modifier(request_store, srp_request, permission_tuple,
                       permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    modifier = mock.sentinel.modifier
    allowed_permissions = (models.PermissionType.review,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.void_modifier(modifier)
    else:
        activity.void_modifier(modifier)
        srp_request.void_modifier.assert_called_once_with(request_store,
                                                          mock.ANY,
                                                          modifier=modifier,
                                                          user=permission_user)


def test_edit_details(request_store, srp_request, permission_tuple,
                      permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    new_details = mock.sentinel.new_details
    allowed_permissions = (('user_id', OWNER_ID),)
    if permission_tuple not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.edit_details(new_details)
    else:
        activity.edit_details(new_details)
        srp_request.change_details.assert_called_once_with(request_store,
                                                           new_details,
                                                           user=permission_user)


def test_set_payout(request_store, srp_request, permission_tuple,
                    permission_user):
    activity = request.RequestActivity(request_store, permission_user,
                                       srp_request)
    new_payout = mock.sentinel.new_payout
    allowed_permissions = (models.PermissionType.review,
                           models.PermissionType.admin)
    if permission_tuple[0] not in allowed_permissions:
        with pytest.raises(errors.InsufficientPermissionsError):
            activity.set_payout(new_payout)
    else:
        activity.set_payout(new_payout)
        srp_request.set_base_payout.assert_called_once_with(request_store,
                                                            new_payout)

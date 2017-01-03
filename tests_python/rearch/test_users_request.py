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


@pytest.fixture
def request_store(srp_request, killmail):
    store = mock.Mock()
    store.get_request.return_value = srp_request
    store.get_killmail.return_value = killmail
    return store


@pytest.fixture(params=models.PermissionType)
def permission(request):
    return request.param


@pytest.mark.parametrize('user_id', (1, 2))
def test_request_init(permission, request_store, srp_request, user_id):
    user = mock.Mock(id_=user_id)
    user.get_permissions.return_value = {
        # Using division #1
        (permission, 1),
        ('user_id', user_id),
    }
    PT = models.PermissionType
    # User ID 1 is the owner, user ID 2 is someone else
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

def test_add_comment():
    pass

try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from evesrp.users import request
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


def test_request_init():
    pass


def test_add_comment():
    pass

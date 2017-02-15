try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from evesrp.users import authorization as authz
from evesrp.users import errors
from evesrp import new_models as models
from evesrp import storage


@pytest.fixture
def store():
    return mock.create_autospec(storage.BaseStore, instance=True)


def test_permissions_admin_init(store):
    user = mock.Mock()
    permissions_admin = authz.PermissionsAdmin(store, user)
    assert permissions_admin.store == store
    assert permissions_admin.user == user


@pytest.fixture(params=[True, False], ids=('is_admin', 'is_not_admin'))
def is_admin(request):
    return request.param


def test_division_create(store, is_admin):
    store.add_division.return_value = 23
    user = mock.Mock(admin=is_admin)
    permissions_admin = authz.PermissionsAdmin(store, user)
    if is_admin:
        division = permissions_admin.create_division('A Division Name')
        assert division is not None
        assert division.name == 'A Division Name'
        assert division.id_ == 23
        store.add_division.assert_called_with(division)
    else:
        with pytest.raises(errors.AdminPermissionError):
            permissions_admin.create_division('Non-Admin Division')


@pytest.mark.parametrize('admin_permission', [True, False])
def test_division_admin_init(store, is_admin, admin_permission):
    user = mock.Mock(admin=is_admin, id_=1)
    division = models.Division('A Division', 1)
    if admin_permission:
        store.get_permissions.return_value = [
            models.Permission(entity_id=user.id_, division=division,
                              type_=models.PermissionType.admin),
        ]
    else:
        store.get_permissions.return_value = []
    if is_admin or admin_permission:
        division_admin = authz.DivisionAdmin(store, user, division)
        assert division_admin is not None
        assert division_admin.division.id_ == division.id_
        assert division_admin.user.id_ == user.id_
        assert division_admin.store == store
    else:
        with pytest.raises(errors.AdminPermissionError):
            authz.DivisionAdmin(store, user, division)


def test_division_admin_list(store):
    user = mock.Mock(admin=True, id_=1)
    division = models.Division('A Division', 31)
    division_admin = authz.DivisionAdmin(store, user, division)
    # Using just plain old mock objects so I can test equivalency/identity
    permissions = [
        mock.Mock(), # submit
        mock.Mock(), # review
        mock.Mock(), # pay
        mock.Mock(), # audit
        mock.Mock(), # admin
    ]
    store.get_permissions.side_effect = permissions
    assert permissions[0] == division_admin.list_permissions(
        models.PermissionType.submit)
    assert permissions[1] == division_admin.list_permissions(
        models.PermissionType.review)
    assert permissions[2] == division_admin.list_permissions(
        models.PermissionType.pay)
    assert permissions[3] == division_admin.list_permissions(
        models.PermissionType.audit)
    assert permissions[4] == division_admin.list_permissions(
        models.PermissionType.admin)
    calls = [
        mock.call(division_id=31, type_=models.PermissionType.submit),
        mock.call(division_id=31, type_=models.PermissionType.review),
        mock.call(division_id=31, type_=models.PermissionType.pay),
        mock.call(division_id=31, type_=models.PermissionType.audit),
        mock.call(division_id=31, type_=models.PermissionType.admin),
    ]
    store.get_permissions.assert_has_calls(calls)

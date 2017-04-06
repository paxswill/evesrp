try:
    from unittest import mock
except ImportError:
    import mock

import pytest
import six

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


@pytest.fixture(params=(True, False), ids=('admin_permission',
                                           'no_admin_permission'))
def has_admin_permission(request):
    return request.param


@pytest.fixture
def store():
    store = storage.MemoryStore()
    return store


@pytest.fixture
def division(store):
    division = store.add_division(u"Testing Division")
    return division


@pytest.fixture
def groups(store, division):
    groups = [
        store.add_group('Submitters 1'),
        store.add_group('Submitters 2'),
        store.add_group('Reviewers 1'),
        store.add_group('Reviewers 2'),
        store.add_group('Payers 1'),
        store.add_group('Payers 2'),
        store.add_group('Auditors 1'),
        store.add_group('Auditors 2'),
        store.add_group('Admins 1'),
        store.add_group('Admins 2'),
    ]
    groups = {g.name: g for g in groups}
    # Only add the first ("___ 1")
    store.add_permission(division.id_, groups['Submitters 1'].id_,
                         models.PermissionType.submit)
    store.add_permission(division.id_, groups['Reviewers 1'].id_,
                         models.PermissionType.review)
    store.add_permission(division.id_, groups['Payers 1'].id_,
                         models.PermissionType.pay)
    store.add_permission(division.id_, groups['Auditors 1'].id_,
                         models.PermissionType.audit)
    store.add_permission(division.id_, groups['Admins 1'].id_,
                         models.PermissionType.admin)
    return groups


@pytest.fixture
def user(store, division, is_admin, has_admin_permission):
    user = store.add_user(u"Test User", is_admin)
    if has_admin_permission:
        store.add_permission(division.id_, user.id_,
                             models.PermissionType.admin)
    return user


class TestPermissionsAdmin(object):

    @pytest.fixture
    def permissions_admin(self, store, user):
        return authz.PermissionsAdmin(store, user)

    def test_division_create(self, store, permissions_admin, is_admin):
        if is_admin:
            division = permissions_admin.create_division(u'Another Division')
            assert division is not None
            assert division.name == u'Another Division'
            assert isinstance(division, models.Division)
            divisions = store.get_divisions()
            assert len(divisions) == 2
        else:
            with pytest.raises(errors.AdminPermissionError):
                permissions_admin.create_division('Non-Admin Permission')

    def test_list_divisions(self, store, permissions_admin, is_admin,
                            has_admin_permission):
        # Add another division to test against
        store.add_division(u'Second Division')
        divisions = permissions_admin.list_divisions()
        if is_admin:
            assert len(divisions) == 2
        elif has_admin_permission:
            assert len(divisions) == 1
        else:
            assert len(divisions) == 0

    @pytest.mark.parametrize('add_groups', (True, False),
                             ids=('add_groups', 'no_add_groups'))
    def test_list_permissions(self, add_groups, store, permissions_admin, user,
                              groups, division, has_admin_permission):
        # Add another division to test against
        store.add_division(u'Second Division')
        if add_groups:
            for group in six.itervalues(groups):
                store.associate_user_group(user.id_, group.id_)
        permissions = permissions_admin.list_permissions()
        if add_groups:
            assert len(permissions) == 1
            assert len(permissions[division]) == 5
        elif has_admin_permission:
            assert len(permissions) == 1
            assert len(permissions[division]) == 1
        else:
            assert len(permissions) == 0


def test_division_admin_init(store, user, division, is_admin,
                             has_admin_permission):
    if is_admin or has_admin_permission:
        division_admin = authz.DivisionAdmin(store, user, division)
        assert division_admin is not None
        assert division_admin.division.id_ == division.id_
        assert division_admin.user.id_ == user.id_
        assert division_admin.store == store
    else:
        with pytest.raises(errors.AdminPermissionError):
            division_admin = authz.DivisionAdmin(store, user, division)


class TestAdminDivision(object):

    @pytest.fixture
    def division_admin(self, store, user, division, has_admin_permission,
                       is_admin):
        if not has_admin_permission and not is_admin:
            pytest.skip("Not testing init failure.")
        return authz.DivisionAdmin(store, user, division)

    @pytest.mark.parametrize('permission_type', models.PermissionType.all,
                             ids=lambda p: p.name)
    def test_list(self, division_admin, permission_type, groups,
                  has_admin_permission):
        # Using the groups fixture just to have some permissions set
        entities = division_admin.list_entities(permission_type)
        if has_admin_permission and \
                permission_type == models.PermissionType.admin:
            assert len(entities) == 2
        else:
            assert len(entities) == 1

    def test_list_all(self, division_admin, groups, user,
                      has_admin_permission):
        # Using the groups fixture just to have some permissions set
        all_permissions = division_admin.list_all_entities()
        assert list(six.iterkeys(all_permissions)) == [
            models.PermissionType.submit,
            models.PermissionType.review,
            models.PermissionType.pay,
            models.PermissionType.audit,
            models.PermissionType.admin,
        ]
        expected_permissions = {
            models.PermissionType.submit: {groups['Submitters 1'], },
            models.PermissionType.review: {groups['Reviewers 1'], },
            models.PermissionType.pay: {groups['Payers 1'], },
            models.PermissionType.audit: {groups['Auditors 1'], },
            models.PermissionType.admin: {groups['Admins 1'], },
        }
        if has_admin_permission:
            expected_permissions[models.PermissionType.admin].add(user)
        assert dict(all_permissions) == expected_permissions


    def test_list_all_available(self, division_admin, groups):
        # Including groups fixture to add a bunch of groups to the store
        entities = set(division_admin.list_all_available_entities())
        # 1 user + 2 groups for each permission type (of which there are 5)
        assert len(entities) == 11

    @pytest.mark.parametrize('action', ('add', 'remove'))
    def test_change_permissions(self, action, store, division_admin, division,
                                groups, is_admin, has_admin_permission):
        if action == 'add':
            method = division_admin.add_permission
            change_groups = {n: g for n, g in six.iteritems(groups)
                             if '2' in n}
        else:
            method = division_admin.remove_permission
            change_groups = {n: g for n, g in six.iteritems(groups)
                             if '1' in n}
        if is_admin or has_admin_permission:
            for name, group in six.iteritems(change_groups):
                if name.startswith('Submitters'):
                    permission = models.PermissionType.submit
                elif name.startswith('Reviewers'):
                    permission = models.PermissionType.review
                elif name.startswith('Payers'):
                    permission = models.PermissionType.pay
                elif name.startswith('Auditors'):
                    permission = models.PermissionType.audit
                elif name.startswith('Admins'):
                    permission = models.PermissionType.admin
                method(group, permission)
                permissions = store.get_permissions(entity_id=group.id_,
                                                    division_id=division.id_,
                                                    type_=permission)
                permissions = set(permissions)
                if action == 'add':
                    assert len(permissions) == 1
                else:
                    assert len(permissions) == 0

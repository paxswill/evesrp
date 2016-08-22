from __future__ import absolute_import
from __future__ import unicode_literals
import pytest
from ..util_tests import TestApp
from evesrp import db
from evesrp.models import Request, Modifier, Action, ActionType
from evesrp.auth import PermissionType
from evesrp.auth.models import Entity, User, Group, Permission, Division,\
    PermissionType, APIKey, Note


@pytest.fixture
def make_group(evesrp_app):
    def _make_group(name):
        group = Group(name, 'AuthMethod')
        db.session.add(group)
        db.session.commit()
        return group
    return _make_group


@pytest.fixture
def make_division(evesrp_app):
    def _make_division(name):
        division = Division(name)
        db.session.add(division)
        db.session.commit()
        return division
    return _make_division


@pytest.fixture(params=PermissionType.all)
def permission(request):
    return request.param


@pytest.fixture
def make_permission(evesrp_app, permission):
    def _make_permission(entity, division):
        perm = Permission(division, permission, entity)
        db.session.commit()
        return perm
    return _make_permission


class TestGroups(object):


    def test_group_membership(self, make_group, user):
        group1 = make_group('One')
        group2 = make_group('Two')
        group1.users.add(user)
        db.session.commit()
        group1_id = group1.id
        group2_id = group2.id
        db.session.expire_all()
        test_user = User.query.get(user.id)
        test_group = Group.query.get(group1_id)
        assert test_user in test_group.users
        test_group = Group.query.get(group2_id)
        assert test_user not in test_group.users


class TestPermissions(object):

    def test_user_permission(self, user, other_user, make_division,
                              make_permission, permission):
        division = make_division('Division A')
        make_permission(user, division)
        db.session.commit()
        assert user.has_permission(permission) 
        assert not other_user.has_permission(permission) 

    def test_user_division_permission(self, user, other_user, make_division,
                                      make_permission, permission):
        division1 = make_division('Division 1')
        division2 = make_division('Division 2')
        make_permission(user, division1)
        make_permission(other_user, division2)
        db.session.commit()
        assert user.has_permission(permission, division1) 
        assert not other_user.has_permission(permission, division1) 
        assert other_user.has_permission(permission, division2) 
        assert not user.has_permission(permission, division2)

    def test_group_permission(self, user, other_user, make_group,
                              make_division, make_permission, permission):
        group = make_group('Group 1')
        other_group = make_group('Group 2')
        group.users.add(user)
        other_group.users.add(other_user)
        division = make_division('Division A')
        make_permission(group, division)
        db.session.commit()
        assert group.has_permission(permission)
        assert not other_group.has_permission(permission)
        assert user.has_permission(permission) 
        assert not other_user.has_permission(permission) 


@pytest.mark.usefixtures('evesrp_app')
@pytest.mark.parametrize('user_role', ['Normal'])
class TestDelete(object):

    def test_delete_api_key(self, user):
        api_key = APIKey(user)
        db.session.add(api_key)
        db.session.commit()
        key_id = api_key.id
        db.session.delete(api_key)
        db.session.commit()
        assert APIKey.query.get(key_id) is None
        assert user is not None

    def test_delete_note(self, user, other_user):
        note = Note(user, other_user, 'A note.')
        db.session.add(note)
        db.session.commit()
        note_id = note.id
        db.session.delete(note)
        db.session.commit()
        assert Note.query.get(note_id) is None
        assert user is not None
        assert other_user is not None

    @pytest.mark.parametrize('permission', [PermissionType.review])
    def test_delete_permission(self, user, make_division, make_permission):
        division = make_division('A Division')
        division_id = division.id
        review_perm = make_permission(user, division)
        review_id = review_perm.id
        db.session.delete(review_perm)
        db.session.commit()
        assert Permission.query.get(review_id) is None
        assert user is not None
        assert Division.query.get(division_id) is not None

    def test_delete_division(self, srp_request):
        permission = Permission.query.filter_by(
                permission=PermissionType.review).one()
        permission_id = permission.id
        division = Division.query.one()
        division_id = division.id
        request = Request.query.one()
        request_id = request.id
        db.session.delete(division)
        db.session.commit()
        assert Division.query.get(division_id) is None
        assert Permission.query.get(permission_id) is None
        assert Request.query.get(request_id) is None

import datetime as dt
try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from evesrp import storage
from evesrp import new_models as models
from evesrp.util import utc


@pytest.fixture
def store():
    return mock.create_autospec(storage.BaseStore, instance=True)


def test_entity_init():
    entity = models.authz.Entity("An Entity", 12345)
    assert entity.name == "An Entity"
    assert entity.id_ == 12345


def test_entity_dict():
    user_dict = {
        'name': 'An Entity',
        'id': 12345,
    }
    entity = models.authz.Entity.from_dict(user_dict)
    assert entity.name == "An Entity"
    assert entity.id_ == 12345


def test_entity_permissions(store):
    PT = models.PermissionType
    entity_perms = [
        models.Permission(entity_id=1, division_id=1, type_=PT.submit),
        models.Permission(entity_id=1, division_id=1, type_=PT.pay),
        models.Permission(entity_id=1, division_id=3, type_=PT.submit),
    ]
    store.get_permissions.return_value = entity_perms
    entity = models.authz.Entity("An Entity", 1)
    permission_tuples = {
        (PT.submit, 1),
        (PT.pay, 1),
        (PT.submit, 3),
    }
    assert entity.get_permissions(store) == permission_tuples


@pytest.mark.parametrize('is_admin', [True, False])
def test_user_init(is_admin):
    user = models.User('A User', 1, is_admin)
    assert user.name == 'A User'
    assert user.id_ == 1
    assert user.admin == is_admin


def test_user_dict():
    user_dict = {
        'name': 'Another User',
        'id': 73,
        'admin': True,
    }
    user = models.User.from_dict(user_dict)
    assert user.name == 'Another User'
    assert user.id_ == 73
    assert user.admin


def test_user_get_groups(store):
    groups = [
        models.Group("Group 1", 1),
        models.Group("Group 3", 3),
    ]
    store.get_groups.return_value = groups
    user = models.User("User 2", 2)
    assert user.get_groups(store) == groups


def test_user_permissions(store):
    PT = models.PermissionType
    # Doing a bit more involved mock here as we want to return different values
    # for store.get_permissions based on the value of entity_id passed in, as
    # well as mocking get_groups
    user1_perms = [
        models.Permission(entity_id=1, division_id=1, type_=PT.submit),
        models.Permission(entity_id=1, division_id=2, type_=PT.review),
    ]
    group2_perms = [
        models.Permission(entity_id=2, division_id=2, type_=PT.review),
        models.Permission(entity_id=2, division_id=2, type_=PT.submit),
        models.Permission(entity_id=2, division_id=3, type_=PT.pay),
    ]
    store.get_groups.return_value = [
        models.Group("Group 2", 2),
    ]

    def get_permissions(entity_id):
        if entity_id == 9:
            return user1_perms
        if entity_id == 2:
            return group2_perms
    store.get_permissions.side_effect = get_permissions
    user = models.User("User 9", 9)
    union_permissions = {
        (PT.submit, 1),
        (PT.review, 2),
        (PT.submit, 2),
        (PT.pay, 3),
        ('user_id', 9),
    }
    assert user.get_permissions(store) == union_permissions


def test_user_notes(store):
    user = models.User("Notable User", 1)
    notes = [
        models.Note("A note.", 1, subject_id=1, submitter_id=2),
    ]
    store.get_notes.return_value = notes
    assert user.get_notes(store) == notes


@pytest.fixture
def group():
    return models.Group("Group 1", 1)


def test_group_get_users(store, group):
    users = [
        models.User("User 2", 2),
        models.User("User 4", 4),
    ]
    store.get_users.return_value = users
    assert group.get_users(store) == users


def test_group_add_user(store, group):
    group.add_user(store, user_id=17)
    store.associate_user_group.assert_called_with(user_id=17,
                                                  group_id=group.id_)


def test_group_remove_user(store, group):
    group.remove_user(store, user_id=17)
    store.disassociate_user_group.assert_called_with(user_id=17,
                                                     group_id=group.id_)


@pytest.fixture
def division():
    return models.Division("A Division", 98765)


def test_division_init(division):
    assert division.name == "A Division"
    assert division.id_ == 98765


def test_division_dict():
    division_dict = {
        'name': 'A Division',
        'id': 98765,
    }
    division = models.Division.from_dict(division_dict)
    assert division.name == "A Division"
    assert division.id_ == 98765


def test_division_add_permission(store, division):
    store.add_permission.return_value = mock.sentinel.added_permission
    permission = division.add_permission(store, entity_id=13,
                                         type_=models.PermissionType.submit)
    assert permission == mock.sentinel.added_permission
    store.add_permission.assert_called_once_with(division.id_, 13,
                                                 models.PermissionType.submit)


def test_division_remove_permission(store, division):
    division.remove_permission(store, permission_id=21)
    store.remove_permission.assert_called_with(permission_id=21)


def test_division_change_name(store, division):
    assert division.name == "A Division"
    division.set_name(store, "A New Name")
    assert division.name == "A New Name"
    store.save_division.assert_called_with(division)


def test_division_get_permissions(store, division):
    mock_permissions = [mock.Mock(id_=1), mock.Mock(id_=2)]
    store.get_permissions.side_effect = mock_permissions
    permissions = division.get_permissions(store)
    assert permissions == mock_permissions[0]
    store.get_permissions.assert_called_with(division_id=division.id_)
    permissions = division.get_permissions(store, models.PermissionType.submit)
    assert permissions == mock_permissions[1]
    store.get_permissions.assert_called_with(division_id=division.id_,
                                             types=(
                                                 models.PermissionType.submit,
                                             ))


def test_permission_init_objects():
    user = models.User("A User", 1357)
    division = models.Division("A Division", 2468)
    permission = models.Permission(entity=user, division=division,
                                   type_=models.PermissionType.submit)
    assert permission.entity_id == user.id_
    assert permission.division_id == division.id_
    assert permission.type_ == models.PermissionType.submit


def test_permission_init_object_ids():
    permission = models.Permission(entity_id=1357, division_id=2468,
                                   type_=models.PermissionType.submit)
    assert permission.entity_id == 1357
    assert permission.division_id == 2468
    assert permission.type_ == models.PermissionType.submit


def test_permission_dict():
    permission_dict = {
        'entity_id': 100,
        'division_id': 200,
        'type': 'submit',
    }
    permission = models.Permission.from_dict(permission_dict)
    assert permission.type_ == models.PermissionType.submit
    assert permission.entity_id == 100
    assert permission.division_id == 200


def test_permission_tuples():
    permission = models.Permission(entity_id=1, division_id=2,
                                   type_=models.PermissionType.review)
    assert permission.to_tuple() == (models.PermissionType.review, 2)


@pytest.mark.parametrize(
    'timestamp',
    (dt.datetime(2016, 12, 10), None, 1),
    ids=('datetime', 'None', 'int')
)
def test_note_init(timestamp):
    contents = u"A note about something."
    # If timestamp is None in the Note __init__, it uses utcnow.
    if timestamp is None:
        before = dt.datetime.utcnow()
    note = models.Note(contents, 1, timestamp, subject_id=2,
                       submitter_id=3)
    if timestamp is None:
        after = dt.datetime.utcnow()
    assert note.id_ == 1
    assert note.subject_id == 2
    assert note.submitter_id == 3
    assert note.contents == contents
    if timestamp is None:
        assert note.timestamp >= before
        assert note.timestamp <= after
    else:
        assert note.timestamp == timestamp


def test_note_dict():
    contents = "Lorem Ipsum blah blah blah"
    note_dict = {
        "id": 11,
        "contents": contents,
        "timestamp": dt.datetime(2016, 12, 10, tzinfo=utc),
        "submitter_id": 22,
        "subject_id": 33,
    }
    note = models.Note.from_dict(note_dict)
    assert note.id_ == 11
    assert note.submitter_id == 22
    assert note.subject_id == 33
    assert note.contents == contents
    assert note.timestamp == dt.datetime(2016, 12, 10, tzinfo=utc)
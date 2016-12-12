import datetime as dt
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp.util import utc
from evesrp.new_models import authorization as authz


def test_entity_init():
    entity = authz.Entity("An Entity", 12345)
    assert entity.name == "An Entity"
    assert entity.id_ == 12345


def test_entity_dict():
    user_dict = {
        'name': 'An Entity',
        'id': 12345,
    }
    entity = authz.Entity.from_dict(user_dict)
    assert entity.name == "An Entity"
    assert entity.id_ == 12345


def test_entity_permissions():
    PT = authz.PermissionType
    entity_perms = [
        authz.Permission(entity_id=1, division_id=1, type_=PT.submit),
        authz.Permission(entity_id=1, division_id=1, type_=PT.pay),
        authz.Permission(entity_id=1, division_id=3, type_=PT.submit),
    ]
    store = mock.Mock()
    store.get_permissions.return_value = entity_perms
    entity = authz.Entity("An Entity", 1)
    permission_tuples = {
        (1, PT.submit),
        (1, PT.pay),
        (3, PT.submit),
    }
    assert entity.get_permissions(store) == permission_tuples


def test_user_get_groups():
    groups = [
        authz.Group("Group 1", 1),
        authz.Group("Group 3", 3),
    ]
    store = mock.Mock()
    store.get_groups.return_value = groups
    user = authz.User("User 2", 2)
    assert user.get_groups(store) == groups


def test_user_permissions():
    PT = authz.PermissionType
    # Doing a bit more involved mock here as we want to return different values
    # for store.get_permissions based on the value of entity_id passed in, as
    # well as mocking get_groups
    user1_perms = [
        authz.Permission(entity_id=1, division_id=1, type_=PT.submit),
        authz.Permission(entity_id=1, division_id=2, type_=PT.review),
    ]
    group2_perms = [
        authz.Permission(entity_id=2, division_id=2, type_=PT.review),
        authz.Permission(entity_id=2, division_id=2, type_=PT.submit),
        authz.Permission(entity_id=2, division_id=3, type_=PT.pay),
    ]
    store = mock.Mock()
    store.get_groups.return_value = [
        authz.Group("Group 2", 2),
    ]
    def get_permissions(entity_id):
        if entity_id == 1:
            return user1_perms
        if entity_id == 2:
            return group2_perms
    store.get_permissions.side_effect = get_permissions
    user = authz.User("User 1", 1)
    union_permissions = {
        (1, PT.submit),
        (2, PT.review),
        (2, PT.submit),
        (3, PT.pay),
    }
    assert user.get_permissions(store) == union_permissions


def test_user_notes():
    user = authz.User("Notable User", 1)
    notes = [
        authz.Note("A note.", 1, subject_id=1, submitter_id=2),
    ]
    store = mock.Mock()
    store.get_notes.return_value = notes
    assert user.get_notes(store) == notes


def test_group_get_users():
    users = [
        authz.User("User 2", 2),
        authz.User("User 4", 4),
    ]
    store = mock.Mock()
    store.get_users.return_value = users
    group = authz.Group("Group 1", 1)
    assert group.get_users(store) == users


def test_division_init():
    division = authz.Division("A Division", 98765)
    assert division.name == "A Division"
    assert division.id_ == 98765


def test_division_dict():
    division_dict = {
        'name': 'A Division',
        'id': 98765,
    }
    division = authz.Division.from_dict(division_dict)
    assert division.name == "A Division"
    assert division.id_ == 98765


def test_permission_init_objects():
    user = authz.User("A User", 1357)
    division = authz.Division("A Division", 2468)
    permission = authz.Permission(entity=user, division=division,
                                  type_=authz.PermissionType.submit)
    assert permission.entity_id == user.id_
    assert permission.division_id == division.id_
    assert permission.type_ == authz.PermissionType.submit


def test_permission_init_object_ids():
    permission = authz.Permission(entity_id=1357, division_id=2468,
                                  type_=authz.PermissionType.submit)
    assert permission.entity_id == 1357
    assert permission.division_id == 2468
    assert permission.type_ == authz.PermissionType.submit


def test_permission_dict():
    permission_dict = {
        'entity_id': 100,
        'division_id': 200,
        'type': 'submit',
    }
    permission = authz.Permission.from_dict(permission_dict)
    assert permission.type_ == authz.PermissionType.submit
    assert permission.entity_id == 100
    assert permission.division_id == 200


def test_permission_tuples():
    permission = authz.Permission(entity_id=1, division_id=2,
                                  type_=authz.PermissionType.review)
    assert permission.to_tuple() == (2, authz.PermissionType.review)


@pytest.mark.parametrize('timestamp', [
    dt.datetime(2016, 12, 10),
    None,
])
def test_note_init(timestamp):
    contents = u"A note about something."
    # If timestamp is None in the Note __init__, it uses utcnow.
    if timestamp is None:
        before = dt.datetime.utcnow()
    note = authz.Note(contents, 1, timestamp, subject_id=2,
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
    note = authz.Note.from_dict(note_dict)
    assert note.id_ == 11
    assert note.submitter_id == 22
    assert note.subject_id == 33
    assert note.contents == contents
    assert note.timestamp == dt.datetime(2016, 12, 10, tzinfo=utc)

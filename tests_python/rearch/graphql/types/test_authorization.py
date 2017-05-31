import pytest
from six.moves import zip

from evesrp.graphql import types
from evesrp import new_models as models


def test_user():
    model = models.User(
        id_=8,
        name=u'User 8',
        admin=True
    )
    user = types.User.from_model(model)
    assert user.id == model.id_
    assert user.name == model.name
    assert user.admin == model.admin


def test_group():
    model = models.Group(
        id_=8000,
        name=u'Group 8000'
    )
    group = types.Group.from_model(model)
    assert group.id == model.id_
    assert group.name == model.name


def test_division():
    model = models.Division(
        id_=80,
        name=u'Division 80'
    )
    division = types.Division.from_model(model)
    assert division.id == model.id_
    assert division.name == model.name


def test_permission_type():
    # It would be easier to just zip up the two, comparing the members of each
    # tuple. But that would require graphene's Enum to act marginally like the
    # standard libary Enum. Which it doesn't. In the most infuriating ways.
    assert models.PermissionType.submit == types.PermissionType.submit
    assert models.PermissionType.review == types.PermissionType.review
    assert models.PermissionType.pay == types.PermissionType.pay
    assert models.PermissionType.admin == types.PermissionType.admin
    assert models.PermissionType.audit == types.PermissionType.audit


def test_permission():
    model = models.Permission(
        division_id=80,
        entity_id=8000,
        type_=models.PermissionType.pay
    )
    permission = types.Permission.from_model(model)
    assert permission.division.id == model.division_id
    assert permission.permission == model.type_
    # NOTE: This is a bit of a cop-out test, permission.entity is set as an int
    # in Permission.from_model, and is then resolved to an actual Entity in
    # Resolver.resolve_permission_field_entity
    assert permission.entity == model.entity_id


def test_note():
    model = models.Note(
        contents=u'Some note contents.',
        id_=7,
        subject_id=8,
        submitter_id=9,
    )
    note = types.Note.from_model(model)
    assert note.id == model.id_
    assert note.subject.id == model.subject_id
    assert note.submitter.id == model.submitter_id
    assert note.timestamp == model.timestamp
    assert note.contents == model.contents

import datetime as dt
import json
import pytest

from evesrp.util import utc

from evesrp.new_models import authorization as authz_models
from evesrp import serializers


def test_serialize_entity():
    entity = authz_models.Entity("An Entity", 1)
    expected_json = """
    {
        "name": "An Entity",
        "id": 1
    }
    """
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(entity, cls=serializers.EntityEncoder))
    assert actual == expected


def test_serialize_user():
    user = authz_models.User("A User", 2)
    expected_json = """
    {
        "name": "A User",
        "id": 2,
        "admin": false
    }
    """
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(user, cls=serializers.UserEncoder))
    assert actual == expected


def test_serialize_group():
    group = authz_models.Group("A Group", 3)
    expected_json = """
    {
        "name": "A Group",
        "id": 3
    }
    """
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(group, cls=serializers.EntityEncoder))
    assert actual == expected


def test_serialize_division():
    division = authz_models.Division("A Division", 4)
    expected_json = """
    {
        "name": "A Division",
        "id": 4
    }
    """
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(division,
                                   cls=serializers.DivisionEncoder))
    assert actual == expected


@pytest.mark.parametrize('permission', authz_models.PermissionType)
def test_serialize_permission_type(permission):
    expected_json = {p: '"{}"'.format(p.value) for p in
                     authz_models.PermissionType}
    expected = json.loads(expected_json[permission])
    actual = json.loads(json.dumps(permission,
                                   cls=serializers.EnumEncoder))
    assert actual == expected


def test_serialize_permission():
    submit = authz_models.PermissionType.submit
    permission = authz_models.Permission(entity_id=1, division_id=2,
                                         type_=submit)
    expected_json = """
    {
        "entity_id": 1,
        "division_id": 2,
        "type": "submit"
    }
    """
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(permission,
                                   cls=serializers.PermissionEncoder))
    assert actual == expected


def test_serialize_note():
    now = dt.datetime.utcnow()
    note = authz_models.Note("A note about a user.", 5,
                             timestamp=now, subject_id=1, submitter_id=2)
    expected_json = """
    {{
        "contents": "A note about a user.",
        "timestamp": "{}",
        "id": 5,
        "subject_id": 1,
        "submitter_id": 2
    }}
    """.format(now.isoformat())
    expected = json.loads(expected_json)
    actual = json.loads(json.dumps(note, cls=serializers.NoteEncoder))
    assert actual == expected

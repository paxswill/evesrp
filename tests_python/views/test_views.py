import datetime as dt
import pytest
from evesrp import db
from evesrp.views import request_count
from evesrp.auth import PermissionType
from evesrp.auth.models import Division, Permission, Pilot
from evesrp.models import Request, ActionType


def test_index_redirect(test_client):
    resp = test_client.get('/')
    assert resp.status_code == 302
    assert '/login/' in resp.headers['Location']


@pytest.mark.parametrize('status', ActionType.statuses)
@pytest.mark.parametrize('permission', (PermissionType.submit,
                                        PermissionType.review,
                                        PermissionType.pay))
@pytest.mark.parametrize('user_role', ['Normal'])
def test_request_count(status, permission, user, user_login):
    """Test (indirectly) that the counts in the nav bar reflect the count of
    requests needing attention.
    """
    division = Division('Counting Division')
    Permission(division, permission, user)
    request_data = {
        'type_name': 'Revenant',
        'type_id': 3514,
        'corporation': 'Center for Advanced Studies',
        'corporation_id': 1000169,
        'kill_timestamp': dt.datetime.utcnow(),
        'system': 'Jita',
        'system_id': 30000142,
        'constellation': 'Kimotoro',
        'constellation_id': 20000020,
        'region': 'The Forge',
        'region_id': 10000002,
        'pilot_id': 1,
    }
    pilot = Pilot(user, 'A Pilot', request_data['pilot_id'])
    Request(user, 'Foo', division, request_data.items(),
            killmail_url='http://example.com', status=status)
    db.session.commit()
    count_combos = {
        (PermissionType.submit, ActionType.incomplete),
        (PermissionType.review, ActionType.evaluating),
        (PermissionType.pay, ActionType.approved),
    }
    with user_login as c:
        c.get('/')
        # test for a status and permission pair
        assert request_count(permission, status) == 1
        # test for the default status for a permission
        if (permission, status) in count_combos:
            assert request_count(permission) == 1
        else:
            assert request_count(permission) == 0

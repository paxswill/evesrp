import datetime as dt
from decimal import Decimal
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp import new_models as models


@pytest.fixture
def paxswill_pilot():
    pilot = models.Pilot("Paxswill", 570140137, user_id=1)
    return pilot


@pytest.fixture
def paxswill_user():
    user = mock.Mock()
    user.id_ = 1
    user.name = "The Real Paxswill"
    return user


@pytest.fixture
def killmail_data():
    return {
        'id': 56474105,
        'pilot_id': 570140137,
        'system_id': 30001445,
        'constellation_id': 20000212,
        'region_id': 10000016,
        'corporation_id': 1018389948,
        'alliance_id': 498125261,
        'type_id': 11202,
        'timestamp': dt.datetime(2016, 10, 7, 15, 22, 56),
    }


@pytest.fixture
def killmail(killmail_data):
    killmail_splat = dict(killmail_data)
    killmail_splat['id_'] = killmail_data['id']
    killmail_splat['user_id'] = 1
    del killmail_splat['id']
    killmail = models.Killmail(**killmail_splat)
    return killmail


@pytest.fixture(params=[None, dt.datetime(2016, 12, 11)])
def nullable_timestamp(request):
    return request.param


# I would normally call this fixture 'request', but that's a special name in
# py.test
@pytest.fixture
def srp_request(killmail, nullable_timestamp):
    request = models.Request(25, u"Some details.",
                             killmail=killmail, division_id=1,
                             timestamp=nullable_timestamp,
                             base_payout=25000000)
    return request



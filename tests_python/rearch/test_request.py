import datetime as dt
from decimal import Decimal
try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from evesrp.new_models import request as models


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


def test_pilot_init(paxswill_pilot):
    pilot = paxswill_pilot
    assert pilot.name == "Paxswill"
    assert pilot.id_ == 570140137
    assert pilot.user_id == 1


def test_pilot_dict():
    pilot_dict = {
        "name": "Paxswill",
        "id": 570140137,
        "user_id": 1,
    }
    pilot = models.Pilot.from_dict(pilot_dict)
    assert pilot.name == "Paxswill"
    assert pilot.id_ == 570140137
    assert pilot.user_id == 1


def test_pilot_get_user(paxswill_pilot, paxswill_user):
    store = mock.Mock()
    store.get_user.return_value = paxswill_user
    assert paxswill_pilot.get_user(store) == paxswill_user


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


def assert_killmail(killmail, killmail_data, user_id):
    assert killmail.id_ == killmail_data['id']
    assert killmail.pilot_id == killmail_data['pilot_id']
    assert killmail.corporation_id == killmail_data['corporation_id']
    assert killmail.alliance_id == killmail_data['alliance_id']
    assert killmail.system_id == killmail_data['system_id']
    assert killmail.constellation_id == killmail_data['constellation_id']
    assert killmail.region_id == killmail_data['region_id']
    assert killmail.type_id == killmail_data['type_id']
    assert killmail.timestamp == killmail_data['timestamp']
    assert killmail.user_id == user_id


def test_killmail_init(killmail, killmail_data):
    assert_killmail(killmail, killmail_data, 1)


def test_killmail_dict(killmail_data):
    killmail_dict = dict(killmail_data)
    killmail_dict['user_id'] = 1
    killmail = models.Killmail.from_dict(killmail_dict)
    assert_killmail(killmail, killmail_data, 1)


def test_killmail_user(killmail, paxswill_user):
    store = mock.Mock()
    store.get_user.return_value = paxswill_user
    assert killmail.get_user(store) == paxswill_user


def test_killmail_pilot(killmail, paxswill_pilot):
    store = mock.Mock()
    store.get_pilot.return_value = paxswill_pilot
    assert killmail.get_pilot(store) == paxswill_pilot


def test_killmail_requests(killmail):
    requests = [
    ]
    store = mock.Mock()
    store.get_requests.return_value = requests
    assert killmail.get_requests(store) == requests


@pytest.fixture
def division():
    division = mock.Mock()
    division.name = "Testing Division"
    division.id_ = 1
    return division


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


def test_request_init(srp_request, nullable_timestamp, killmail):
    assert srp_request.id_ == 25
    assert srp_request.details == 'Some details.'
    assert srp_request.killmail_id == killmail.id_
    assert srp_request.division_id == 1
    if nullable_timestamp is None:
        assert srp_request.timestamp != dt.datetime(2016, 12, 11)
    else:
        assert srp_request.timestamp == dt.datetime(2016, 12, 11)
    assert srp_request.status == models.ActionType.evaluating
    assert srp_request.base_payout == Decimal(25000000)
    assert srp_request.payout == srp_request.base_payout


def test_request_dict():
    request_dict = {
        "id": 27,
        "details": u"Gimme money please.",
        "killmail_id": 56474105,
        "division_id": 2,
        "timestamp": dt.datetime(2016, 12, 11),
        "status": "approved",
        "base_payout": "25000000",
        # In this test case, the payout is not actually a real value.
        "payout": "42000000",
    }
    srp_request = models.Request.from_dict(request_dict)
    assert srp_request.id_ == 27
    assert srp_request.details == u"Gimme money please."
    assert srp_request.killmail_id ==56474105
    assert srp_request.division_id == 2
    assert srp_request.timestamp == dt.datetime(2016, 12, 11)
    assert srp_request.status == models.ActionType.approved
    assert srp_request.base_payout == Decimal(25000000)
    assert srp_request.payout == Decimal(42000000)


def test_request_actions(srp_request):
    mock_actions = [1, 2, 3, 4]
    store = mock.Mock()
    store.get_actions.return_value = mock_actions
    assert srp_request.get_actions(store) == mock_actions


@pytest.fixture
def mock_modifiers():
    MT = models.ModifierType
    mock_modifiers = [
        mock.Mock(type_=MT.absolute, value=Decimal(1000000), is_void=True),
        mock.Mock(type_=MT.relative, value=Decimal("0.25"), is_void=True),
        mock.Mock(type_=MT.absolute, value=Decimal(3000000), is_void=False),
        mock.Mock(type_=MT.relative, value=Decimal("0.1"), is_void=False),
    ]
    return mock_modifiers


@pytest.fixture
def mock_modifiers_store(mock_modifiers):
    store = mock.Mock()
    def modifiers_filtering(request_id, void=None, type_=None):
        filtered_list = mock_modifiers
        if void is not None:
            filtered_list = filter(lambda m: m.is_void == void, filtered_list)
        if type_ is not None:
            filtered_list = filter(lambda m: m.type_ == type_, filtered_list)
        return list(filtered_list)
    store.get_modifiers.side_effect = modifiers_filtering
    return store


@pytest.mark.parametrize('void,type_', [
    (None, None),
    (None, models.ModifierType.absolute),
    (None, models.ModifierType.relative),
    (True, None),
    (True, models.ModifierType.absolute),
    (True, models.ModifierType.relative),
    (False, None),
    (False, models.ModifierType.absolute),
    (False, models.ModifierType.relative),
])
def test_request_modifiers(srp_request, void, type_, mock_modifiers,
                           mock_modifiers_store):
    # Hard-code in the expected result, as programmatic filtering would just
    # get the same result.
    expected_modifiers = {
        (None, None): mock_modifiers,
        (None, models.ModifierType.absolute): [mock_modifiers[0],
                                               mock_modifiers[2]],
        (None, models.ModifierType.relative): [mock_modifiers[1],
                                               mock_modifiers[3]],
        (True, None): mock_modifiers[:2],
        (True, models.ModifierType.absolute): [mock_modifiers[0]],
        (True, models.ModifierType.relative): [mock_modifiers[1]],
        (False, None): mock_modifiers[2:],
        (False, models.ModifierType.absolute): [mock_modifiers[2]],
        (False, models.ModifierType.relative): [mock_modifiers[3]],
    }
    assert srp_request.get_modifiers(mock_modifiers_store,
                                     void=void, type_=type_) == \
        expected_modifiers[(void, type_)]


def test_request_division(srp_request):
    division = mock.Mock()
    division.name = "Testing Division"
    division.id = 1
    store = mock.Mock()
    store.get_division.return_value = division
    assert srp_request.get_division(store) == division


def test_request_killmail(srp_request, killmail):
    store = mock.Mock()
    store.get_killmail.return_value = killmail
    assert srp_request.get_killmail(store) == killmail


@pytest.mark.parametrize('status', models.ActionType)
def test_request_current_status(srp_request, status):
    AT = models.ActionType
    actions = [
        mock.Mock(type_=status),
        mock.Mock(type_=AT.comment),
    ]
    store = mock.Mock()
    store.get_actions.return_value = actions
    if status == AT.comment:
        expected_status = AT.evaluating
    else:
        expected_status = status
    assert srp_request.current_status(store) == expected_status


added_modifiers = [
    None,
    mock.Mock(type_=models.ModifierType.absolute, value=Decimal(1000000),
              is_void=False),
    mock.Mock(type_=models.ModifierType.relative, value=Decimal("0.2"),
              is_void=False),
    mock.Mock(type_=models.ModifierType.absolute, value=Decimal(-4000000),
              is_void=False),
    mock.Mock(type_=models.ModifierType.relative, value=Decimal("-0.3"),
              is_void=False),
]
@pytest.mark.parametrize('added_modifier', added_modifiers)
def test_request_current_payout(srp_request, mock_modifiers,
                                mock_modifiers_store, added_modifier):
    if added_modifier is not None:
        mock_modifiers.append(added_modifier)
    expected_results = {
        # (25,000,000 + 3,000,000) * (1 + 0.1) = 30,800,000
        added_modifiers[0]: Decimal(30800000),
        # (25,000,000 + 4,000,000) * (1 + 0.1) = 31,900,000
        added_modifiers[1]: Decimal(31900000),
        # (25,000,000 + 3,000,000) * (1 + 0.3) = 36,400,000
        added_modifiers[2]: Decimal(36400000),
        # (25,000,000 - 1,000,000) * (1 + 0.1) = 26,400,000
        added_modifiers[3]: Decimal(26400000),
        # (25,000,000 + 3,000,000) * (1 - 0.2) = 22,400,000
        added_modifiers[4]: Decimal(22400000),
    }
    assert srp_request.current_payout(mock_modifiers_store) == \
        expected_results[added_modifier]


def test_action_init(nullable_timestamp):
    if nullable_timestamp is None:
        before = dt.datetime.utcnow()
    action = models.Action(10, models.ActionType.approved,
                           timestamp=nullable_timestamp,
                           request_id=7, user_id=2)
    if nullable_timestamp is None:
        after = dt.datetime.utcnow()
    assert action.id_ == 10
    assert action.type_ == models.ActionType.approved
    if nullable_timestamp is None:
        assert action.timestamp >= before
        assert action.timestamp <= after
    else:
        assert action.timestamp == dt.datetime(2016, 12, 11)
    assert action.contents == ''
    assert action.request_id == 7
    assert action.user_id == 2


def test_action_dict():
    action_dict = {
        "id": 10,
        "type": "comment",
        "timestamp": dt.datetime(2016, 12, 3),
        "request_id": 4,
        "user_id": 2,
        "contents": u"A legitimate comment.", 
    }
    action = models.Action.from_dict(action_dict)
    assert action.id_ == action_dict['id']
    assert action.type_ == models.ActionType.comment
    assert action.timestamp == action_dict['timestamp']
    assert action.request_id == action_dict['request_id']
    assert action.user_id == action_dict['user_id']
    assert action.contents == action_dict['contents']


@pytest.fixture
def modifier(nullable_timestamp):
    modifier = models.Modifier(5, models.ModifierType.relative, 0.1,
                               u'Because I said so.',
                               timestamp=nullable_timestamp,
                               request_id=7, user_id=1)
    return modifier


def test_modifier_init(modifier, nullable_timestamp):
    assert modifier.id_ == 5
    assert modifier.type_ == models.ModifierType.relative
    assert modifier.value == Decimal(0.1)
    assert modifier.note == u'Because I said so.'
    if nullable_timestamp is None:
        assert modifier.timestamp != nullable_timestamp
    else:
        assert modifier.timestamp == nullable_timestamp
    assert modifier.request_id == 7
    assert modifier.user_id == 1
    assert modifier.void_timestamp == None
    assert modifier.void_user_id == None


@pytest.mark.parametrize('voided', [True, False])
def test_modifier_dict(voided):
    modifier_dict = {
        "id": 4,
        "type": "relative",
        # value is a string, to preserve precision
        "value": "0.25",
        "note": u"Just a note.",
        "user_id": 1,
        "request_id": 7,
        "timestamp": dt.datetime(2016, 12, 11, 12),
    }
    if voided:
        modifier_dict['void'] = {
            "user_id": 1,
            "timestamp": dt.datetime(2016, 12, 11, 12, 3),
        }
    else:
        modifier_dict['void'] = None
    modifier = models.Modifier.from_dict(modifier_dict)
    assert modifier.id_ == modifier_dict['id']
    assert modifier.type_ == models.ModifierType.relative
    assert modifier.value == Decimal(modifier_dict['value'])
    assert modifier.note == modifier_dict['note']
    assert modifier.user_id == modifier_dict['user_id']
    assert modifier.request_id == modifier_dict['request_id']
    assert modifier.timestamp == modifier_dict['timestamp']
    assert modifier.is_void == voided
    if voided:
        assert modifier.void_timestamp == modifier_dict['void']['timestamp']
        assert modifier.void_user_id == modifier_dict['void']['user_id']


def test_modifier_is_void(modifier):
    assert not modifier.is_void
    modifier.void_user_id = 1
    modifier.void_timestamp = dt.datetime.utcnow()
    assert modifier.is_void


def test_modifier_void(modifier):
    assert not modifier.is_void
    modifier.void(user_id=1, timestamp=dt.datetime(2016, 12, 1))
    assert modifier.is_void
    assert modifier.void_user_id == 1
    assert modifier.void_timestamp == dt.datetime(2016, 12, 1)

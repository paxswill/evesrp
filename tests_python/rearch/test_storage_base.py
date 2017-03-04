import inspect
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp import storage
from evesrp import search_filter as sfilter


not_implemented = [
    'get_authn_user', 'add_authn_user', 'save_authn_user',
    'get_authn_group', 'add_authn_group', 'save_authn_user',
    'get_division', 'get_divisions', 'add_division', 'save_division',
    'get_permission', 'get_permissions', 'add_permission', 'remove_permission',
    'get_user', 'add_user', 'get_users', 
    'get_group', 'add_group', 'get_groups', 'associate_user_group',
    'disassociate_user_group',
    'get_killmail', 'get_killmails',
    'get_request', 'get_requests', 'add_request', 'save_request',
    'get_action', 'get_actions', 'add_action',
    'get_modifier', 'get_modifiers', 'add_modifier', 'save_modifier',
    'filter_requests',
    'get_pilot', 'get_notes',
]


@pytest.mark.parametrize('method_name', not_implemented)
def test_not_implemented(method_name):
    store = storage.BaseStore()
    method = getattr(store, method_name)
    # subtract one for self
    arg_count = len(inspect.getargspec(method).args) - 1
    with pytest.raises(NotImplementedError):
        # This silliness with the range splat is just to fill in required
        # arguments.
        method(*range(arg_count))


@pytest.fixture
def mock_filter_store():
    store = storage.BaseStore()
    store.filter_requests = mock.Mock()
    store.get_pilot = mock.Mock()
    store.get_division = mock.Mock()
    store.get_killmails = mock.Mock()
    return store


@pytest.fixture(params=(
    ('killmail_id', 'submit_timestamp'),
    ('killmail_id', 'kill_timestamp'),
    ('killmail_id', 'division'),
    ('killmail_id', 'pilot'),
    pytest.mark.xfail(('killmail_id', 'type')),
), ids=(
    'simple_request',
    'simple_request_simple_killmail',
    'simple_request_combo_request_app',
    'simple_request_combo_killmail_app',
    'simple_request_combo_killmail_cpp',
))
def fields(request):
    return request.param


@pytest.mark.parametrize('single_killmail', (True, False),
                         ids=('single_killmail', 'multiple_killmails'))
def test_format_sparse(mock_filter_store, fields, single_killmail):
    format_kwargs = {}
    if 'kill_timestamp' in fields or \
            'pilot' in fields or \
            'type' in fields:
        # We need to create a fake killmail
        killmail = {
            'id': 1234,
            'pilot_id': 2468,
            'type_id': 1357,
            'timestamp': mock.sentinel.kill_timestamp,
        }
        if single_killmail:
            format_kwargs['killmail'] = killmail
        else:
            format_kwargs['killmails'] = {
                killmail['id']:killmail,
            }
        if 'pilot' in fields:
            mock_filter_store.get_pilot.return_value = {
                'name': mock.sentinel.pilot_name,
            }
    request = {
        'killmail_id': 1234,
        'timestamp': mock.sentinel.submit_timestamp,
        'division_id': 8642,
    }
    if 'division' in fields:
        mock_filter_store.get_division.return_value = {
            'name': mock.sentinel.division_name,
        }
    sparse_request = mock_filter_store._format_sparse(
        request, fields, **format_kwargs)
    assert set(sparse_request.keys()) == set(fields)
    assert sparse_request['killmail_id'] == 1234
    if 'submit_timestamp' in fields:
        assert sparse_request['submit_timestamp'] == \
            mock.sentinel.submit_timestamp
    if 'kill_timestamp' in fields:
        assert sparse_request['kill_timestamp'] == \
            mock.sentinel.kill_timestamp
    if 'division' in fields:
        assert sparse_request['division'] == {
            'id': 8642,
            'name': mock.sentinel.division_name,
        }
        mock_filter_store.get_division.assert_called_with(8642)
    else:
        assert not mock_filter_store.get_division.called
    if 'pilot' in fields:
        assert sparse_request['pilot'] == {
            'id': 2468,
            'name': mock.sentinel.pilot_name,
        }
        mock_filter_store.get_pilot.assert_called_with(2468)
    else:
        assert not mock_filter_store.get_pilot.called
    if 'type' in fields:
        assert sparse_request['type'] == {
            'id': None,
            'name': mock.sentinel
        }


def test_format_sparse_exception():
    store = storage.BaseStore()
    with pytest.raises(ValueError):
        store._format_sparse(dict(), {'kill_timestamp',})


def test_filter_sparse(mock_filter_store, fields):
    mock_filter_store.filter_requests.return_value = [
        {'killmail_id': 1,},
        {'killmail_id': 2,},
        {'killmail_id': 3,},
    ]
    mock_filter_store.get_killmails.return_value = [
        {'id': 1,},
        {'id': 2,},
        {'id': 3,},
    ]
    mock_filter_store._format_sparse = mock.Mock()
    mock_filter_store._format_sparse.return_value = mock.sentinel.sparse
    sparse_requests = list(mock_filter_store.filter_sparse(
        mock.sentinel.filters, fields))
    mock_filter_store.filter_requests.assert_called_with(mock.sentinel.filters)
    if 'kill_timestamp' in fields or \
            'pilot' in fields or \
            'type' in fields:
        mock_filter_store.get_killmails.assert_called_with(
            killmail_ids=set((1, 2, 3)))
    else:
        assert not mock_filter_store.get_killmails.called
    assert sparse_requests == [
        mock.sentinel.sparse,
        mock.sentinel.sparse,
        mock.sentinel.sparse,
    ]


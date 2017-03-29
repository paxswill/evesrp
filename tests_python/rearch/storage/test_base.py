import inspect
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp import storage


not_implemented = [
    'get_authn_user', 'add_authn_user', 'save_authn_user',
    'get_authn_group', 'add_authn_group', 'save_authn_user',
    'get_division', 'get_divisions', 'add_division', 'save_division',
    'get_permissions', 'add_permission', 'remove_permission',
    'get_user', 'add_user', 'get_users',
    'get_group', 'add_group', 'get_groups',
    'associate_user_group', 'disassociate_user_group',
    'get_killmail', 'add_killmail',
    'get_request', 'get_requests', 'add_request', 'save_request',
    'get_action', 'get_actions', 'add_action',
    'get_modifier', 'get_modifiers', 'add_modifier', 'void_modifier',
    'filter_requests',
    'get_character', 'get_characters', 'add_character', 'save_character',
    'get_notes', 'add_note',
    'get_region', 'get_constellation', 'get_system',
    'get_alliance', 'get_corporation', 'get_ccp_character',
    'get_type',
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


def test_get_killmails():
    store = storage.BaseStore()
    store.get_killmail = mock.Mock()

    def mock_get_killmail(killmail_id):
        return getattr(mock.sentinel, 'killmail_' + str(killmail_id))
    store.get_killmail.side_effect = mock_get_killmail
    sentinel_killmails = {getattr(mock.sentinel, 'killmail_' + str(i))
                          for i in range(4)}
    assert sentinel_killmails == set(store.get_killmails(range(4)))


@pytest.fixture
def mock_filter_store():
    store = storage.BaseStore()
    store.filter_requests = mock.Mock()
    store.get_character = mock.Mock()
    store.get_division = mock.Mock()
    store.get_killmails = mock.Mock()
    return store


@pytest.fixture(params=(
    ('killmail_id', 'request_timestamp'),
    ('killmail_id', 'killmail_timestamp'),
    ('killmail_id', 'division_id'),
    ('killmail_id', 'character_name'),
    ('killmail_id', 'type_id'),
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
    if 'killmail_timestamp' in fields or \
            'character_name' in fields or \
            'type_id' in fields:
        # We need to create a fake killmail
        killmail = mock.Mock(id_=1234, character_id=mock.sentinel.character_id,
                             type_id=mock.sentinel.type_id,
                             timestamp=mock.sentinel.kill_timestamp)
        if single_killmail:
            format_kwargs['killmail'] = killmail
        else:
            format_kwargs['killmails'] = {
                killmail.id_: killmail,
            }
        if 'character_name' in fields:
            character_mock = mock.Mock(id_=mock.sentinel.character_id)
            character_mock.name = mock.sentinel.character_name
            mock_filter_store.get_character.return_value = character_mock
    request = mock.Mock(killmail_id=1234,
                        timestamp=mock.sentinel.submit_timestamp,
                        division_id=8642)
    if 'division_id' in fields:
        division_mock = mock.Mock()
        division_mock.name = mock.sentinel.division_name
        mock_filter_store.get_division.return_value = division_mock
    sparse_request = mock_filter_store._format_sparse(
        request, fields, **format_kwargs)
    assert set(sparse_request.keys()) == set(fields)
    assert sparse_request['killmail_id'] == 1234
    if 'request_timestamp' in fields:
        assert sparse_request['request_timestamp'] == \
            mock.sentinel.submit_timestamp
    if 'killmail_timestamp' in fields:
        assert sparse_request['killmail_timestamp'] == \
            mock.sentinel.kill_timestamp
    if 'division' in fields:
        assert sparse_request['division_id'] == division_mock
        mock_filter_store.get_division.assert_called_with(8642)
    else:
        assert not mock_filter_store.get_division.called
    if 'character_name' in fields:
        assert sparse_request['character_name'] == mock.sentinel.character_name
        mock_filter_store.get_character.assert_called_with(
            character_id=mock.sentinel.character_id)
    else:
        assert not mock_filter_store.get_character.called
    if 'type_id' in fields:
        assert sparse_request['type_id'] == mock.sentinel.type_id


def test_format_sparse_exception():
    store = storage.BaseStore()
    with pytest.raises(TypeError):
        store._format_sparse(dict(), {'killmail_timestamp', })


def test_filter_sparse(mock_filter_store, fields):
    mock_filter_store.filter_requests.return_value = [
        mock.Mock(killmail_id=1),
        mock.Mock(killmail_id=2),
        mock.Mock(killmail_id=3),
    ]
    mock_filter_store.get_killmails.return_value = [
        mock.Mock(id_=1),
        mock.Mock(id_=2),
        mock.Mock(id_=3),
    ]
    mock_filter_store._format_sparse = mock.Mock()
    mock_filter_store._format_sparse.return_value = mock.sentinel.sparse
    sparse_requests = list(mock_filter_store.filter_sparse(
        mock.sentinel.filters, fields))
    mock_filter_store.filter_requests.assert_called_with(mock.sentinel.filters)
    if 'killmail_timestamp' in fields or \
            'character_name' in fields or \
            'type_id' in fields:
        mock_filter_store.get_killmails.assert_called_with(
            killmail_ids=set((1, 2, 3)))
    else:
        assert not mock_filter_store.get_killmails.called
    assert sparse_requests == [
        mock.sentinel.sparse,
        mock.sentinel.sparse,
        mock.sentinel.sparse,
    ]

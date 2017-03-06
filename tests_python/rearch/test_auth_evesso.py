import itertools
try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from evesrp.new_auth import evesso


@pytest.fixture
def context():
    get_rv = mock.Mock()
    get_rv.json.return_value = {
        'CharacterID': 570140137,
        'CharacterName': 'Paxswill',
        'CharacterOwnerHash': 'PaxswillOwnerHash',
        'ExpiresOn': '2017-03-05T02:46:53',
        'IntellectualProperty': 'EVE',
        'Scopes': 'publicData',
        'TokenType': 'Character',
    }
    session = mock.Mock()
    session.get.return_value = get_rv
    session.token = mock.sentinel.token
    return {
        'oauth_session': session,
    }


@pytest.fixture
def store():
    store = mock.Mock()
    store.get_corporation_id.return_value = 1018389948
    store.get_corporation_name.return_value = 'Dreddit'
    store.get_alliance_id.return_value = 498125261
    store.get_alliance_name.return_value = 'Test Alliance Please Ignore'
    return store


@pytest.mark.parametrize('existing_authn_user,logged_in_user', (
    (True, None),
    (False, True),
    (False, False),
))
def test_get_user(context, existing_authn_user, logged_in_user):
    store = mock.Mock()
    if existing_authn_user:
        store.get_authn_user.return_value = mock.sentinel.authn_user
        current_user = None
    else:
        store.get_authn_user.return_value = None
        store.add_authn_user.return_value = mock.sentinel.authn_user
        if logged_in_user:
            current_user = mock.Mock(id_=mock.sentinel.current_user_id)
        else:
            current_user = None
            store.add_user.return_value = mock.Mock(
                id_=mock.sentinel.current_user_id)
    provider = evesso.EveSsoProvider(store, client_id=None, client_secret=None)
    # mock out the provider's _update_user_token method
    provider._update_user_token = mock.Mock()
    assert provider.get_user(context, current_user=current_user) == {
        'user': mock.sentinel.authn_user,
    }
    store.get_authn_user.assert_called_once_with(mock.ANY, 'PaxswillOwnerHash')
    if not existing_authn_user:
        store.add_authn_user.assert_called_once_with(
            user_id=mock.sentinel.current_user_id,
            provider_uuid=mock.ANY,
            provider_key='PaxswillOwnerHash')
        if not logged_in_user:
            store.add_user.assert_called_once_with('Paxswill')
    provider._update_user_token.assert_called_once_with(
        mock.sentinel.authn_user,
        mock.sentinel.token)


def test_get_characters(context, store):
    provider = evesso.EveSsoProvider(store, client_id=None, client_secret=None)
    assert provider.get_characters(context) == {
        'characters': [
            {
                'name': 'Paxswill',
                'id': 570140137,
            },
        ],
    }


@pytest.mark.parametrize('existing_groups', (True, False))
def test_get_groups(context, store, existing_groups):
    provider = evesso.EveSsoProvider(store, client_id=None, client_secret=None)
    if existing_groups:
        store.get_authn_group.side_effect = (
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        )
    else:
        store.get_authn_group.return_value = None
        store.add_authn_group.side_effect = (
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        )
    assert provider.get_groups(context) == {
        'groups': [
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        ],
    }
    assert store.get_authn_group.call_args_list == [
        mock.call(mock.ANY, '1018389948'),
        mock.call(mock.ANY, '498125261'),
    ]
    if not existing_groups:
        assert store.add_group.call_count == 2
        assert store.add_authn_group.call_count == 2
        store.add_group.assert_any_call('Dreddit')
        store.add_authn_group.assert_any_call(group_id=mock.ANY,
            provider_uuid=mock.ANY, provider_key='1018389948')
        store.add_group.assert_any_call('Test Alliance Please Ignore')
        store.add_authn_group.assert_any_call(group_id=mock.ANY,
            provider_uuid=mock.ANY, provider_key='498125261')

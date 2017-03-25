try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from evesrp import storage
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


@pytest.fixture(params=(True, False),
                ids=('inside_alliance', 'outside_alliance'))
def in_alliance(request):
    return request.param

@pytest.fixture
def store(in_alliance):
    store = mock.create_autospec(storage.BaseStore)
    if in_alliance:
        store.get_corporation.return_value = {
            u'id': 1018389948,
            u'name': u'Dreddit',
        }
        store.get_alliance.return_value = {
            u'id': 498125261,
            u'name': u'Test Alliance Please Ignore',
        }
    else:
        store.get_corporation.return_value = {
            u'id': 1018389948,
            u'name': u'Dreddit',
        }
        store.get_alliance.side_effect = storage.NotInAllianceError(
            'character', 'testing')
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
        store.get_authn_user.side_effect = storage.NotFoundError('authn_user',
                                                                 'testing')
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
    assert provider.get_user(context, current_user=current_user) == \
        mock.sentinel.authn_user
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
    assert provider.get_characters(context) == [
        {
            'name': u'Paxswill',
            'id': 570140137,
        },
    ]


@pytest.mark.parametrize('existing_groups', (True, False))
def test_get_groups(context, store, existing_groups, in_alliance):
    provider = evesso.EveSsoProvider(store, client_id=None, client_secret=None)
    if existing_groups:
        store.get_authn_group.side_effect = (
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        )
    else:
        store.get_authn_group.side_effect = storage.NotFoundError(
            'authn_group', 'testing')
        store.add_authn_group.side_effect = (
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        )
        store.add_group.side_effect = (
            mock.Mock(id_=mock.sentinel.corp_group_id),
            mock.Mock(id_=mock.sentinel.alliance_group_id),
        )
    if in_alliance:
        assert provider.get_groups(context) == [
            mock.sentinel.authn_corp_group,
            mock.sentinel.authn_alliance_group,
        ]
        assert store.get_authn_group.call_args_list == [
            mock.call(mock.ANY, '1018389948'),
            mock.call(mock.ANY, '498125261'),
        ]
    else:
        assert provider.get_groups(context) == [
            mock.sentinel.authn_corp_group,
        ]
        assert store.get_authn_group.call_args_list == [
            mock.call(mock.ANY, '1018389948'),
        ]

    if not existing_groups:
        store.add_group.assert_any_call('Dreddit')
        store.add_authn_group.assert_any_call(
            group_id=mock.sentinel.corp_group_id,
            provider_uuid=provider.uuid,
            provider_key='1018389948')
        if in_alliance:
            assert store.add_group.call_count == 2
            assert store.add_authn_group.call_count == 2
            store.add_group.assert_any_call('Test Alliance Please Ignore')
            store.add_authn_group.assert_any_call(
                group_id=mock.sentinel.alliance_group_id,
                provider_uuid=provider.uuid,
                provider_key='498125261')
        else:
            assert store.add_group.call_count == 1
            assert store.add_authn_group.call_count == 1

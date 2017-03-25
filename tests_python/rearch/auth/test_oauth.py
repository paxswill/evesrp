import datetime as dt
import itertools
try:
    from unittest import mock
except ImportError:
    import mock
import uuid

import pytest
from oauthlib.oauth2 import OAuth2Error

from evesrp import storage
from evesrp.new_auth import oauth


@pytest.fixture(autouse=True)
def patch_oauth(monkeypatch):
    mock_session = mock.Mock()
    monkeypatch.setattr(oauth, 'OAuth2Session', mock_session)
    return mock_session


@pytest.mark.parametrize('use_refresh,use_get,scope,token_expiry',
                         itertools.product((True, False), repeat=4))
def test_oauth_provider_init(use_refresh, use_get, scope, token_expiry):
    store = mock.create_autospec(storage.BaseStore)
    provider_kwargs = {
        'client_id': mock.sentinel.client_id,
        'client_secret': mock.sentinel.client_secret,
        'authorize_url': mock.sentinel.authorize_url,
        'access_token_url': mock.sentinel.access_token_url,
    }
    if use_refresh:
        provider_kwargs['refresh_token_url'] = mock.sentinel.refresh_token_url
    if use_get:
        provider_kwargs['method'] = 'GET'
    if scope:
        provider_kwargs['scope'] = mock.sentinel.scope
    if token_expiry:
        provider_kwargs['default_token_expiry'] = mock.sentinel.token_expiry
    provider = oauth.OAuthProvider(store, **provider_kwargs)
    assert provider.store == store
    assert provider.client_id == mock.sentinel.client_id
    assert provider.client_secret == mock.sentinel.client_secret
    assert provider.authorize_url == mock.sentinel.authorize_url
    assert provider.token_url == mock.sentinel.access_token_url
    if use_refresh:
        assert provider.refresh_url == mock.sentinel.refresh_token_url
    else:
        assert provider.refresh_url is None
    if use_get:
        assert provider.oauth_method == 'GET'
    else:
        assert provider.oauth_method == 'POST'
    if scope:
        assert provider.scope == mock.sentinel.scope
    else:
        assert provider.scope is None
    if token_expiry:
        assert provider.default_token_expiry == mock.sentinel.token_expiry
    else:
        assert provider.default_token_expiry == 300


def test_oauth_uuid():
    provider1 = oauth.OAuthProvider(None,
                                    client_id='Foo',
                                    client_secret='Bar',
                                    authorize_url='Baz',
                                    access_token_url=None)
    provider2 = oauth.OAuthProvider(None,
                                    client_id='Baz',
                                    client_secret='Qux',
                                    authorize_url='Zot',
                                    access_token_url=None)
    assert provider1.uuid == uuid.UUID('fa790662-1ab8-5ede-965c-94d5ea5d2bee')
    assert provider2.uuid != provider1.uuid


@pytest.mark.parametrize('add_expiration,add_refresh',
                         itertools.product((True, False), repeat=2))
def test_oauth_token_for_user(add_expiration, add_refresh):
    user = mock.Mock()
    user.access_token = mock.sentinel.access_token
    extra_data = {}
    user.extra_data = extra_data
    if add_refresh:
        extra_data['refresh_token'] = None
        user.refresh_token = mock.sentinel.refresh_token
    if add_expiration:
        extra_data['expiration'] = None
        user.expiration = dt.datetime(2017, 3, 3, 11, 0)
    # Mock out utcnow so we always have a set time to base against (used
    # for expiry stuff).
    utcnow_mock = mock.Mock(return_value=dt.datetime(2017, 3, 3, 10, 0))
    with mock.patch('datetime.datetime', utcnow=utcnow_mock):
        token = oauth.OAuthProvider.token_for_user(user)
    expected = {
        'token_type': 'Bearer',
        'access_token': mock.sentinel.access_token,
    }
    if add_refresh:
        expected['refresh_token'] = mock.sentinel.refresh_token
    if add_expiration:
        expected['expires_in'] = 3600
    else:
        expected['expires_in'] = 0
    assert token == expected


@pytest.fixture(params=(True, False))
def use_refresh(request):
    return request.param


@pytest.fixture
def provider(use_refresh):
    if use_refresh:
        refresh_url = mock.sentinel.refresh_url
    else:
        refresh_url = None
    provider = oauth.OAuthProvider(None,
                                   client_id=mock.sentinel.client_id,
                                   client_secret=mock.sentinel.client_secret,
                                   authorize_url=mock.sentinel.authorize_url,
                                   refresh_token_url=refresh_url,
                                   access_token_url=mock.sentinel.access_url)
    return provider


def test_oauth_context_refresh(patch_oauth, use_refresh, provider):
    user = mock.Mock()
    user.access_token = mock.sentinel.access_token
    user.extra_data = {}
    if use_refresh:
        user.extra_data['refresh_token'] = None
        user.refresh_token = mock.sentinel.refresh_token
    patch_oauth.return_value = mock.sentinel.user_oauth_session
    ctx = provider.create_context(user=user)
    assert len(ctx) == 2
    assert ctx['action'] == 'success'
    assert ctx['context'] == {
        'oauth_session': mock.sentinel.user_oauth_session,
    }
    assert patch_oauth.call_count == 1
    call = patch_oauth.call_args
    assert call[0] == (mock.sentinel.client_id,)
    kwargs = call[1]
    assert 'token' in kwargs
    if use_refresh:
        assert kwargs['auto_refresh_url'] == mock.sentinel.refresh_url
        assert 'auto_refresh_kwargs' in kwargs


@pytest.mark.parametrize('fail', (True, False))
def test_oauth_context_code(patch_oauth, provider, fail):
    session_instance = mock.Mock()
    patch_oauth.return_value = session_instance
    session_instance.fetch_token.return_value = mock.sentinel.token
    if fail:
        session_instance.fetch_token.side_effect = OAuth2Error
    ctx = provider.create_context(code=mock.sentinel.code,
                                  redirect_uri=mock.sentinel.redirect_uri)
    assert patch_oauth.call_args_list[0] == mock.call(
        mock.sentinel.client_id, redirect_uri=mock.sentinel.redirect_uri)
    session_instance.fetch_token.assert_called_once_with(
        mock.sentinel.access_url,
        code=mock.sentinel.code,
        method='POST',
        client_secret=mock.sentinel.client_secret,
        auth=(mock.sentinel.client_id,
              mock.sentinel.client_secret)
    )
    if fail:
        assert patch_oauth.call_count == 1
        assert ctx == {
            'action': 'error',
            'error': None,
        }
    else:
        assert patch_oauth.call_count == 2
        assert patch_oauth.call_args_list[1] == mock.call(
            mock.sentinel.client_id, token=mock.sentinel.token)
        assert ctx['action'] == 'success'
        assert ctx['context'] == {
            'oauth_session': session_instance,
        }


def test_oauth_context_redirect(patch_oauth, provider):
    session_instance = mock.Mock()
    patch_oauth.return_value = session_instance
    session_instance.authorization_url.return_value = (
        mock.sentinel.external_url,
        mock.sentinel.state,
    )
    redirect_uri = mock.sentinel.redirect_uri
    ctx = provider.create_context(redirect_uri=redirect_uri)
    assert ctx == {
        'action': 'redirect',
        'url': mock.sentinel.external_url,
        'state': mock.sentinel.state,
    }
    patch_oauth.assert_called_once_with(mock.sentinel.client_id,
                                        redirect_uri=redirect_uri,
                                        scope=None)


@pytest.mark.parametrize('default_expiry', (True, False))
def test_oauth_token_saver(patch_oauth, use_refresh, default_expiry):
    user = mock.Mock()
    store = mock.create_autospec(storage.BaseStore)
    provider = oauth.OAuthProvider(store,
                                   client_id=mock.sentinel.client_id,
                                   client_secret=None,
                                   authorize_url=None,
                                   access_token_url=None)
    # Replace provider.get_user with a mock, as the normal one raises
    # NotImplementedError
    provider.get_user = mock.Mock(return_value=user)
    token = {
        u'access_token': mock.sentinel.access_token,
        # 180 seconds is 3 minutes
        u'expires_in': 180,
    }
    if default_expiry:
        del token[u'expires_in']
    if use_refresh:
        token[u'refresh_token'] = mock.sentinel.refresh_token
    # patch utcnow so we can rely on how long tokens are valid for
    utcnow_mock = mock.Mock(return_value=dt.datetime(2017, 3, 3, 10, 0))
    with mock.patch('datetime.datetime', utcnow=utcnow_mock):
        provider.token_saver(token)
    # Assert that the user's data was updated
    assert user.access_token == mock.sentinel.access_token
    if use_refresh:
        assert user.refresh_token == mock.sentinel.refresh_token
    if default_expiry:
        assert user.expiration == dt.datetime(2017, 3, 3, 10, 0)
    else:
        assert user.expiration == dt.datetime(2017, 3, 3, 10, 3)
    # Now check other things
    patch_oauth.assert_called_once_with(mock.sentinel.client_id,
                                        token=token)
    store.save_authn_user.assert_called_once_with(user)


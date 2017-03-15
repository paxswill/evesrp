from __future__ import absolute_import

import datetime as dt
import uuid

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import OAuth2Error

from .base import AuthenticationProvider


class OAuthProvider(AuthenticationProvider):

    __namespace_uuid = uuid.UUID('9f7074f9-be29-41b8-bd00-45b945e05bb1')

    def __init__(self, store, **kwargs):
        # OAuth Provider specific information
        self.client_id = kwargs.pop('client_id')
        self.client_secret = kwargs.pop('client_secret')
        self.authorize_url = kwargs.pop('authorize_url')
        self.token_url = kwargs.pop('access_token_url')
        # refresh_url is None if refresh is not supported
        self.refresh_url = kwargs.pop('refresh_token_url', None)
        self.oauth_method = kwargs.pop('method', 'POST')
        self.scope = kwargs.pop('scope', None)
        self.default_token_expiry = kwargs.pop('default_token_expiry', 300)
        super(OAuthProvider, self).__init__(store, **kwargs)

    @property
    def uuid(self):
        name = '{s.authorize_url}{s.client_id}{s.client_secret}'.format(s=self)
        return uuid.uuid5(self.__namespace_uuid, name)

    @staticmethod
    def token_for_user(authn_user):
        token = {
            'token_type': 'Bearer',
            'access_token': authn_user.access_token,
        }
        if 'expiration' in authn_user.extra_data:
            now = dt.datetime.utcnow()
            remaining_time = authn_user.expiration - now
            token['expires_in'] = int(remaining_time.total_seconds())
        else:
            token['expires_in'] = 0
        if 'refresh_token' in authn_user.extra_data:
            token['refresh_token'] = authn_user.refresh_token
        return token

    def create_context(self, **kwargs):
        if 'user' in kwargs:
            # We're creating a session from a stored access token or getting a
            # new access token with a refresh token. If that's not possible,
            # we're returning an error.
            user = kwargs['user']
            token = self.token_for_user(user)
            session_kwargs = {
                'token': token,
            }
            if self.refresh_url is not None and 'refresh_token' in token:
                session_kwargs.update(
                    auto_refresh_url=self.refresh_url,
                    auto_refresh_kwargs={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                    })
            oauth_session = OAuth2Session(self.client_id, **session_kwargs)
            return {
                'action': 'success',
                'context': {
                    'oauth_session': oauth_session,
                }
            }
        elif 'code' in kwargs:
            # We're in the second part of the OAuth dance, where the resource
            # owner has already authenticated themselves to the provider and
            # authorized our application's access. We now need to fetch an
            # access token.
            oauth_session = OAuth2Session(self.client_id,
                                          redirect_uri=kwargs['redirect_uri'])
            try:
                # NOTE: state checking **MUST** be done outside of this method
                token = oauth_session.fetch_token(
                    self.token_url, code=kwargs['code'],
                    method=self.oauth_method,
                    client_secret=self.client_secret,
                    auth=(self.client_id, self.client_secret))
            except OAuth2Error as e:
                return {
                    'action': 'error',
                    'error': e.error,
                }
            oauth_session = OAuth2Session(self.client_id, token=token)
            return {
                'action': 'success',
                'context': {
                    'oauth_session': oauth_session,
                }
            }
        else:
            oauth_session = OAuth2Session(self.client_id,
                                          redirect_uri=kwargs['redirect_uri'],
                                          scope=self.scope)
            redirect_url, state = oauth_session.authorization_url(
                self.authorize_url)
            return {
                'action': 'redirect',
                'url': redirect_url,
                'state': state,
            }

    def _update_user_token(self, user, token):
        now = dt.datetime.utcnow()
        user.access_token = token[u'access_token']
        if u'refresh_token' in token:
            user.refresh_token = token[u'refresh_token']
        expires_in = token.get(u'expires_in', 0)
        user.expiration = now + dt.timedelta(seconds=expires_in)
        self.store.save_authn_user(user)

    def token_saver(self, token):
        oauth_session = OAuth2Session(self.client_id, token=token)
        user = self.get_user({'oauth_session': oauth_session})
        self._update_user_token(user, token)

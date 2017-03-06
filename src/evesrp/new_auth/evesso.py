from __future__ import absolute_import
import datetime as dt

from oauthlib.oauth2 import OAuth2Error

from evesrp import new_models as models
from evesrp.new_auth.oauth import OAuthProvider


class EveSsoProvider(OAuthProvider):

    def __init__(self, store, sisi=False, **kwargs):
        if sisi:
            self.domain = 'https://sisilogin.testeveonline.com'
        else:
            self.domain = 'https://login.eveonline.com'
        kwargs.setdefault('access_token_url', self.domain + '/oauth/token')
        kwargs.setdefault('authorize_url', self.domain + '/oauth/authorize')
        kwargs.setdefault('refresh_token_url', self.domain + '/oauth/token')
        kwargs.setdefault('scope', ['publicData'])
        kwargs.setdefault('method', 'POST')
        super(EveSsoProvider, self).__init__(store, **kwargs)

    def _get_user_data(self, context):
        session = context['oauth_session']
        try:
            resp = session.get(self.domain + '/oauth/verify').json()
        except OAuth2Error as e:
            return {
                'error': e,
            }
        try:
            return {
                'result': {
                    'name': resp[u'CharacterName'],
                    'id': resp[u'CharacterID'],
                    'owner_hash': resp[u'CharacterOwnerHash'],
                },
            }
        except KeyError:
            return {
                'error': "Error in receiving EVE SSO response: {}".format(resp),
            }

    def get_user(self, context, current_user=None):
        user_data = self._get_user_data(context)
        if 'error' in user_data:
            return user_data
        user_data = user_data['result']
        authn_user = self.store.get_authn_user(self.uuid,
                                               user_data['owner_hash'])
        if authn_user is None:
            if current_user is None:
                current_user = self.store.add_user(user_data['name'])
            authn_user = self.store.add_authn_user(
                user_id=current_user.id_,
                provider_uuid=self.uuid,
                provider_key=user_data['owner_hash'])
        self._update_user_token(authn_user, context['oauth_session'].token)
        return {
            'user': authn_user,
        }

    def get_characters(self, context):
        user_data = self._get_user_data(context)
        if 'error' in user_data:
            return user_data
        user_data = user_data['result']
        return {
            'characters': [
                {
                    'name': user_data['name'],
                    'id': user_data['id'],
                }
            ],
        }

    def get_groups(self, context):
        user_data = self._get_user_data(context)
        if 'error' in user_data:
            return user_data
        user_data = user_data['result']
        corp_id = self.store.get_corporation_id(character_id=user_data['id'])
        alliance_id = self.store.get_alliance_id(corporation_id=corp_id)
        # NOTE If there's future progress on uniting different
        # AuthNProviders' corp and alliance groups, this part will need
        # to be modified
        corp_authn_group = self.store.get_authn_group(self.uuid, str(corp_id))
        if corp_authn_group is None:
            corp_name = self.store.get_corporation_name(corp_id)
            corp_group = self.store.add_group(corp_name)
            corp_authn_group = self.store.add_authn_group(
                group_id=corp_group.id_, provider_uuid=self.uuid,
                provider_key=str(corp_id))
        alliance_authn_group = self.store.get_authn_group(self.uuid,
                                                          str(alliance_id))
        if alliance_authn_group is None:
            alliance_name = self.store.get_alliance_name(alliance_id)
            alliance_group = self.store.add_group(alliance_name)
            alliance_authn_group = self.store.add_authn_group(
                group_id=alliance_group.id_, provider_uuid=self.uuid,
                provider_key=str(alliance_id))
        return {
            'groups': [
                corp_authn_group,
                alliance_authn_group,
            ],
        }

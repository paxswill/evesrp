from __future__ import absolute_import
import collections

from oauthlib.oauth2 import OAuth2Error
import six

from .oauth import OAuthProvider
from .errors import RemoteLoginError
from evesrp import storage


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
        kwargs.setdefault('name', u"EVE SSO")
        super(EveSsoProvider, self).__init__(store, **kwargs)

    @property
    def fields(self):
        # Instead of a simbple submit button, CCP prefers a fancy image is
        # used.
        fields = collections.OrderedDict()
        # Yes, this is mixing presentation and logic a bit here
        fields[u'submit'] = (u'Log In with EVE Online', 'evesso.png')
        return fields

    def _get_user_data(self, context):
        session = context['oauth_session']
        try:
            resp = session.get(self.domain + '/oauth/verify')
        except OAuth2Error as e:
            remote_exc = RemoteLoginError("Error getting user details from EVE"
                                          " SSO.")
            six.raise_from(remote_exc, e)
        try:
            resp_json = resp.json()
            return {
                'name': resp_json[u'CharacterName'],
                'id': resp_json[u'CharacterID'],
                'owner_hash': resp_json[u'CharacterOwnerHash'],
            }
        except (KeyError, ValueError) as old_exc:
            new_exc = RemoteLoginError("Error in parsing EVE SSO response.",
                                       resp)
            six.raise_from(new_exc, old_exc)

    def get_user(self, context, current_user=None):
        user_data = self._get_user_data(context)
        try:
            authn_user = self.store.get_authn_user(self.uuid,
                                                   user_data['owner_hash'])
        except storage.NotFoundError:
            if current_user is None:
                current_user = self.store.add_user(user_data['name'])
            authn_user = self.store.add_authn_user(
                user_id=current_user.id_,
                provider_uuid=self.uuid,
                provider_key=user_data['owner_hash'])
        self._update_user_token(authn_user, context['oauth_session'].token)
        return authn_user

    def get_characters(self, context):
        user_data = self._get_user_data(context)
        return [
            {
                'name': user_data['name'],
                'id': user_data['id'],
            },
        ]

    def get_groups(self, context):
        # NOTE If there's future progress on uniting different
        # AuthNProviders' corp and alliance groups, this part will need
        # to be modified
        user_data = self._get_user_data(context)
        groups = []
        # Find/create a corporation group
        corp_info = self.store.get_corporation(character_id=user_data['id'])
        try:
            corp_authn_group = self.store.get_authn_group(
                self.uuid, str(corp_info['id']))
        except storage.NotFoundError:
            corp_group = self.store.add_group(corp_info[u'name'])
            corp_authn_group = self.store.add_authn_group(
                group_id=corp_group.id_, provider_uuid=self.uuid,
                provider_key=str(corp_info['id']))
        groups.append(corp_authn_group)
        # If the corp is in an alliance, find.create a group for that as well.
        try:
            alliance_info = self.store.get_alliance(
                corporation_id=corp_info[u'id'])
        except storage.NotInAllianceError:
            pass
        else:
            try:
                alliance_authn_group = self.store.get_authn_group(
                    self.uuid, str(alliance_info['id']))
            except storage.NotFoundError:
                alliance_group = self.store.add_group(alliance_info[u'name'])
                alliance_authn_group = self.store.add_authn_group(
                    group_id=alliance_group.id_, provider_uuid=self.uuid,
                    provider_key=str(alliance_info['id']))
            groups.append(alliance_authn_group)
        return groups

    def is_admin(self, context):
        user_data = self._get_user_data(context)
        user_name = user_data[u'name']
        return user_name in self.admins

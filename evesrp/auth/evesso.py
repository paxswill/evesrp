from __future__ import absolute_import
from flask import request, current_app, abort
from sqlalchemy.orm.exc import NoResultFound

from .oauth import OAuthMethod, OAuthUser
from .. import db
from .models import Group, Pilot


class EveSSO(OAuthMethod):

    def __init__(self, singularity=False, **kwargs):
        if not singularity:
            crest_root_url = 'https://crest-tq.eveonline.com/'
        else:
            # SiSi Crest doesn't seem to work over HTTPS yet
            crest_root_url = 'http://public-crest-sisi.testeveonline.com'
        # CREST URLs are all specified as absolute URLs, so skip setting a base
        # URL
        kwargs.setdefault('base_url', u'')
        # Discover the OAuth endpoints by looking in the CREST root
        crest_resp = current_app.requests_session.get(crest_root_url)
        self.crest_root = crest_resp.json()
        crest_token_url = self.crest_root[u'authEndpoint'][u'href']
        kwargs.setdefault('authorize_url',
                crest_token_url.replace('token', 'authorize'))
        kwargs.setdefault('access_token_url', crest_token_url)
        kwargs.setdefault('access_token_method', 'POST')
        kwargs.setdefault('content_type', 'application/json')
        kwargs.setdefault('app_key', 'EVE_SSO')
        kwargs.setdefault('name', u'EVE SSO')
        super(EveSSO, self).__init__(**kwargs)

    def _get_user_data(self, token):
        if not hasattr(request, '_user_data'):
            resp = self.oauth.get('verify', token=token)
            try:
                char_data = {
                    'name': resp.data[u'CharacterName'],
                    'id': resp.data[u'CharacterID'],
                }
                request._user_data = char_data
            except (TypeError, KeyError):
                abort(500, u"Error in receiving EVE SSO response: {}".format(
                        resp.data))
        return request._user_data

    def get_user(self, token):
        character = self._get_user_data(token)
        try:
            user = OAuthUser.query.filter_by(name=character['name'],
                    authmethod=self.name).one()
        except NoResultFound:
            user = OAuthUser(character['name'], self.name,
                    token=token['access_token'])
            db.session.add(user)
            db.session.commit()
        return user

    def get_pilots(self, token):
        # The EVE SSO API only authenticates one character at a time, so we're
        # going to have a 1-to-1 mapping of Users to Pilots
        character = self._get_user_data(token)
        pilot = Pilot.query.get(int(character['id']))
        if pilot is None:
            pilot = Pilot(None, character['name'], character['id'])
            db.session.add(pilot)
            db.session.commit()
        return [pilot]

    def get_groups(self, token):
        # No groups for Eve SSO. Maybe sometime in the future we'll be able to
        # use SSO as a restricted way to get access to the rest of the API,
        # like to look up a user's mailing lists and then create groups from
        # that.
        return []

from __future__ import absolute_import
from flask import request
from sqlalchemy.orm.exc import NoResultFound

from .oauth import OAuthMethod, OAuthUser
from .. import db
from .models import Group, Pilot


class EveSSO(OAuthMethod):

    def __init__(self, singularity=False, **kwargs):
        if not singularity:
            domain = 'https://login.eveonline.com'
        else:
            domain = 'https://sisilogin.testeveonline.com'

        kwargs.setdefault('authorize_url',
                domain + '/oauth2/authorize')
        kwargs.setdefault('access_token_url',
                domain + '/oauth2/token')
        kwargs.setdefault('base_url',
                domain + '/oauth/')
        kwargs.setdefault('access_token_method', 'POST')
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

from __future__ import absolute_import
from flask import request, current_app, abort
from sqlalchemy.orm.exc import NoResultFound
from flask.ext.wtf import Form

from .oauth import OAuthMethod, OAuthUser
from .. import db
from .models import Group, Pilot
from ..util.fields import ImageField
from ..versioned_static import static_file


class EveSSO(OAuthMethod):

    def __init__(self, singularity=False, **kwargs):
        # CREST URLs are all specified as absolute URLs, so skip setting a base
        # URL
        kwargs.setdefault('base_url', u'')
        # Set a member for the crest URLs
        if not singularity:
            self.root_urls = {
                'public': 'https://public-crest.eveonline.com/',
                'authed': 'https://crest-tq.eveonline.com/',
            }
        else:
            self.root_urls = {
                'public': 'http://public-crest-sisi.testeveonline.com/',
                'authed': 'https://api-sisi.testeveonline.com/',
            }
        # Discover the OAuth endpoints by looking in the CREST root
        public_resp = current_app.requests_session.get(
                self.root_urls['public'])
        public_root = public_resp.json()
        crest_token_url = public_root[u'authEndpoint'][u'href']
        kwargs.setdefault('access_token_url', crest_token_url)
        kwargs.setdefault('authorize_url',
                crest_token_url.replace('token', 'authorize'))

        kwargs.setdefault('access_token_method', 'POST')
        kwargs.setdefault('content_type', 'application/json')
        kwargs.setdefault('app_key', 'EVE_SSO')
        kwargs.setdefault('name', u'EVE SSO')
        super(EveSSO, self).__init__(**kwargs)

    def _get_user_data(self, token):
        if not hasattr(request, '_user_data'):
            # Get the public CREST root to infer where the verification
            # endpoint is
            public_resp = current_app.requests_session.get(
                    self.root_urls['public'])
            public_root = public_resp.json()
            verify_url = public_root[u'authEndpoint'][u'href'].replace(
                    'token', 'verify')
            resp = self.oauth.get(verify_url, token=token)
            current_app.logger.debug(u"SSO lookup results: {}".format(
                    resp.data))
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

    def form(self):
        class EveSSOForm(Form):
            submit = ImageField(src=static_file('evesso.png'),
                    alt=u"Log in with EVE Online")

        return EveSSOForm

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

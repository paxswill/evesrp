from __future__ import absolute_import
from flask import request
from sqlalchemy.orm.exc import NoResultFound

from .. import db
from .oauth import OAuthMethod, OAuthUser
from .models import Group, Pilot


class J4OAuth(OAuthMethod):

    def __init__(self, base_url='https://j4lp.com/oauth/api/v1/', **kwargs):
        """:py:class:`~.AuthMethod` for using
        `J4OAuth <https://github.com/J4LP/J4OAuth>`_ as an authentication
        source.

        :param str authorize_url: The URL to request OAuth authorization
            tokens. Default:
            ``'https://j4lp.com/oauth/authorize'``.
        :param str access_token_url: The URL for OAuth token exchange. Default:
            ``'https://j4lp.com/oauth/token'``.
        :param str base_str: The base URL for API requests. Default:
            ``'https://j4lp.com/oauth/api/v1/'``.
        :param dict request_token_params: Additional parameters to include with
            the authorization token request. Default: ``{'scope':
            ['auth_info', 'auth_groups', 'characters']}``.
        :param str access_token_method: HTTP Method to use for exchanging
            authorization tokens for access tokens. Default: ``'GET'``.
        :param str name: The name for this authentication method. Default:
            ``'J4OAuth'``.
        """
        self.base_url = base_url
        kwargs.setdefault('access_token_url', 'https://j4lp.com/oauth/token')
        kwargs.setdefault('authorize_url', 'https://j4lp.com/oauth/authorize')
        kwargs.setdefault('access_token_method', 'GET')
        kwargs.setdefault('request_token_params',
                {'scope': ['auth_info', 'auth_groups', 'characters']})
        kwargs.setdefault('name', u'J4OAuth')
        super(J4OAuth, self).__init__(**kwargs)

    def _get_user_data(self):
        if not hasattr(request, '_auth_user_data'):
            resp = self.session.get('auth_user').json()
            request._auth_user_data = resp[u'user']
        return request._auth_user_data

    def get_user(self):
        auth_user = self._get_user_data()
        try:
            user = OAuthUser.query.filter_by(name=auth_user['main_character'],
                                            authmethod=self.name).one()
        except NoResultFound:
            user = OAuthUser(name=auth_user['main_character'],
                    authmethod=self.name)
            db.session.add(user)
            db.session.commit()
        return user

    def get_pilots(self):
        pilots = []
        resp = self.session.get(self.base_url + 'characters').json()
        auth_characters = resp[u'characters']
        for character in auth_characters:
            pilot = Pilot.query.get(int(character[u'characterID']))
            if pilot is None:
                # Pass 'None' as the user, it will get set later
                pilot = Pilot(None, character[u'characterName'],
                        character[u'characterID'])
                db.session.add(pilot)
            pilots.append(pilot)
        db.session.commit()
        return pilots

    def get_groups(self):
        groups = []
        resp = self.session.get(self.base_url + 'auth_groups').json()
        auth_groups = resp[u'groups']
        # Append the user's alliance to the normal list of groups
        auth_user = self._get_user_data(token)
        auth_groups.append(u'{} alliance'.format(auth_user[u'alliance']))
        # Create/Retrieve Group objects for every group name
        for group_name in auth_groups:
            try:
                group = Group.query.filter_by(name=group_name,
                        authmethod=self.name).one()
            except NoResultFound:
                group = Group(group_name, self.name)
                db.session.add(group)
            groups.append(group)
        db.session.commit()
        return groups

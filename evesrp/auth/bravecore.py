from __future__ import absolute_import
from ecdsa import SigningKey, VerifyingKey, NIST256p
from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app, request
from hashlib import sha256
from binascii import unhexlify
from copy import deepcopy

from .. import db
from ..util import ensure_unicode
from . import AuthMethod, AuthForm
from .models import User, Group, Pilot


class BraveCore(AuthMethod):
    def __init__(self, client_key, server_key, identifier,
            url='https://core.braveineve.com', **kwargs):
        """
        Authentication method using a `Brave Core
        <https://github.com/bravecollective/core>`_ instance.

        Uses the native Core API to authenticate users. Currently only supports
        a single character at a time due to limitations in Core's API.

        :param client_key: The client's private key.
        :type client_key: :py:class:`ecdsa.SigningKey`
        :param server_key: The server's public key for this app.
        :type server_key: :py:class:`ecdsa.VerifyingKey`
        :param str identifier: The identifier for this app in Core.
        :param str url: The URL of the Core instance to authenticate against.
            Default: 'https://core.braveineve.com'
        :param str name: The user-facing name for this authentication method.
            Default: 'Brave Core'
        """
        self._identifier = identifier
        self._client_key = client_key
        self._server_key = server_key
        if 'name' not in kwargs:
            kwargs['name'] = u'Brave Core'
        super(BraveCore, self).__init__(**kwargs)

    # BraveCore.api is now a property so that accessing current_app is delayed
    # until the app is totally set up. Accessing current_app fails until the
    # app is properly initialized, and the current application needs to be
    # accessed to get the requests_session for it for Brave's API.
    # Hopefully sometime in the future this can be removed, maybe when I
    # actually write that OAuth provider for Core.
    @property
    def api(self):
        if not hasattr(self, '_api'):
            self._api = API(self._identifier, self._client_key,
                    self._server_key, current_app.requests_session)
        return self._api

    def login(self, form):
        # Redirect to Core for the authorization token. Give URLs to return to.
        # Sidenote: At this time, Brave has nearly 0 API documentation. The
        # kinda-sorta hidden TEST Auth API documentation is more complete.
        result_url = url_for('login.auth_method_login', _external=True,
                auth_method=self.safe_name)
        response = self.api.core.authorize(success=result_url,
                failure=result_url)
        core_url = response[u'location']
        return redirect(core_url)

    def view(self):
        token = ensure_unicode(request.args.get('token'))
        if token is not None:
            info = self.api.core.info(token=token)
            # Fail if we don't get anything back from Core
            if info is None:
                flash(u"Login failed.", u'error')
                current_app.logger.info(u"Empty response from Core API for "
                                        u"token {}".format(token))
                return redirect(url_for('login.login'))
            char_name = info.character.name
            try:
                user = CoreUser.query.filter_by(name=char_name,
                        authmethod=self.name).one()
                user.token = token
            except NoResultFound:
                user = CoreUser(name=char_name, authmethod=self.name,
                        token=token)
                db.session.add(user)
            # Apply admin flag
            user.admin = user.name in self.admins
            # Sync up group membership
            for group_name in info.tags:
                try:
                    group = CoreGroup.query.filter_by(name=group_name,
                            authmethod=self.name).one()
                except NoResultFound:
                    group = CoreGroup(group_name, self.name)
                    db.session.add(group)
                user.groups.add(group)
            user_groups = deepcopy(user.groups)
            for group in user_groups:
                if group.name not in info.tags and group in user.groups:
                    user.groups.remove(group)
            # Sync pilot (just the primary for now)
            pilot = Pilot.query.get(info.character.id)
            if not pilot:
                pilot = Pilot(user, char_name, info.character.id)
                db.session.add(pilot)
            else:
                pilot.user = user
            db.session.commit()
            self.login_user(user)
            return redirect(url_for('index'))
        else:
            flash(u"Login failed.", u'error')
            return redirect(url_for('login.login'))


class CoreUser(User):

    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    #: The token given by Core to retrieve information about this user.
    #: Typically valid for 30 days.
    token = db.Column(db.String(100, convert_unicode=True))


class CoreGroup(Group):

    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)

    description = db.Column(db.Text(convert_unicode=True))

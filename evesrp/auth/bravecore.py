from __future__ import absolute_import
from ecdsa import SigningKey, VerifyingKey, NIST256p
from braveapi.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app, request
from hashlib import sha256
from binascii import unhexlify
from copy import deepcopy

from .. import db
from ..util import ensure_unicode
from . import AuthMethod
from .models import User, Group, Pilot


class BraveCore(AuthMethod):
    def __init__(self, client_key, server_key, identifier,
            url='https://core.braveineve.com', **kwargs):
        """
        Authentication method using a `Brave Core
        <https://github.com/bravecollective/core>`_ instance.

        Uses the native Core API to authenticate users. Currently only supports
        a single character at a time due to limitations in Core's API.

        :param str client_key: The client's private key in hex form.
        :param str server_key: The server's public key for this app in hex form.
        :param str identifier: The identifier for this app in Core.
        :param str url: The URL of the Core instance to authenticate against.
            Default: 'https://core.braveineve.com'
        :param str name: The user-facing name for this authentication method.
            Default: 'Brave Core'
        """
        # Allow raw object instances of the keys for the time being
        # Client Key
        if not isinstance(client_key, SigningKey):
            try:
                client_key = self.hex2key(client_key)
            except ValueError:
                raise ValueError(u"BraveCore: client_key must be the key in "
                                 u"hex form.")
        # Server Key
        if not isinstance(server_key, VerifyingKey):
            try:
                server_key = self.hex2key(server_key)
            except ValueError:
                raise ValueError(u"BraveCore: server_key must be the key in "
                                 u"hex form.")
        self.api = API(url, identifier, client_key, server_key,
                current_app.requests_session).api        
        if 'name' not in kwargs:
            kwargs['name'] = u'Brave Core'
        super(BraveCore, self).__init__(**kwargs)

    @staticmethod
    def hex2key(hex_key):
        key_bytes = unhexlify(hex_key)
        if len(hex_key) == 64:
            return SigningKey.from_string(key_bytes, curve=NIST256p,
                    hashfunc=sha256)
        elif len(hex_key) == 128:
            return VerifyingKey.from_string(key_bytes, curve=NIST256p,
                    hashfunc=sha256)
        else:
            raise ValueError("Key in hex form is of the wrong length.")

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

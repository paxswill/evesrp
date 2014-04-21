from ecdsa import SigningKey, VerifyingKey, NIST256p
from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app
from hashlib import sha256
from binascii import unhexlify

from .. import db, requests_session
from . import AuthMethod, AuthForm
from .models import User, Group


class BraveCore(AuthMethod):
    name = 'Brave Core'

    def __init__(self, **kwargs):
        try:
            config = kwargs['config']
        except KeyError:
            client_key = kwargs['client_key']
            server_key = kwargs['server_key']
            identifier = kwargs['identifier']
            try:
                url = kwargs['url']
            except KeyError:
                url = 'https://core.bravecollective.net/api'
        else:
            client_key = config['CORE_AUTH_PRIVATE_KEY']
            server_key = config['CORE_AUTH_PUBLIC_KEY']
            identifier = config['CORE_AUTH_IDENTIFIER']
            try:
                url = config['CORE_AUTH_URL']
            except KeyError:
                url = 'https://core.bravecollective.net/'

        if isinstance(client_key, SigningKey):
            # Is the value a key object?
            priv = client_key
        elif hasattr(client_key, 'read'):
            # Is the value a file opject to a PEM encoded key?
            priv_pem = client_key.read()
            priv = SigningKey.from_pem(priv_pem, hashfunc=sha256)
        else:
            try:
                # Is the value the filename of a PEM encoded key?
                with open(client_key, 'r') as f:
                    priv_pem = f.read()
                    priv = SigningKey.from_pem(priv_pem, hashfunc=sha256)
            except FileNotFoundError:
                # Is the value a hex encoded key?
                priv = SigningKey.from_string(unhexlify(client_key),
                        curve=NIST256p, hashfunc=sha256)

        # GO through the entire process again for the public key
        if isinstance(server_key, VerifyingKey):
            pub = server_key
        elif hasattr(server_key, 'read'):
            pub_pem = server_key.read()
            pub = VerifyingKey.from_pem(pub_pem)
        else:
            try:
                with open(server_key, 'r') as f:
                    pub_pem = f.read()
                    pub = VerifyingKey.from_pem(pub_pem)
            except FileNotFoundError:
                pub = VerifyingKey.from_string(unhexlify(server_key),
                        curve=NIST256p, hashfunc=sha256)

        self.api = API(url, identifier, priv, pub,
                requests_session).api

    def login(self, form):
        # Redirect to Core for the authorization token. Give URLs to return to.
        # Sidenote: At this time, Brave has nearly 0 API documentation. The
        # kinda-sorta hidden TEST Auth API documentation is more complete.
        result_url = url_for('login.auth_method_login', _external=True,
                auth_method=self.__class__.__name__.lower())
        response = self.api.core.authorize(success=result_url,
                failure=result_url)
        core_url = response['location']
        return redirect(core_url)

    def list_groups(self, user=None):
        pass

    def view(self):
        token = request.args.get('token')
        if token is not None:
            try:
                user = BraveCoreUser.query.filter_by(token=token).one()
            except NoResultFound:
                user = BraveCoreUser(token=token)
                db.session.add(user)
            # update user information
            info = self.api.core.info(token=token)
            user.name = info['character']['name']
            # Sync up group membership
            for tag in info['tags']:
                try:
                    group = BraveCoreGroup.query.filter_by(core_id=tag).one()
                except NoResultFound:
                    group = BraveCoreGroup()
                    group.core_id = tag
                    # TODO: Figure out how to get the Group name
                    db.session.add(group)
                user.groups.append(group)
            for tag in user.groups.difference(info['tags']):
                group = BraveCoreGroup.query.filter_by(core_id=tag).one()
                user.groups.remove(group)
            db.session.commit()
            self.login_user(user)
            # TODO Have a meaningful redirect for this
            return redirect(url_for('index'))
        else:
            flash("Login failed.")
            return redirect(url_for('login.login'))


class BraveCoreUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    token = db.Column(db.String(100))

    @classmethod
    def authmethod(cls):
        return BraveCore


class BraveCoreGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    core_id = db.Column(db.Integer, index=True)
    description = db.Column(db.Text)

    @classmethod
    def authmethod(cls):
        return BraveCore

from ecdsa import SigningKey, VerifyingKey
from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app
from flask.ext.principal import identity_changed, Identity

from .. import db, auth_methods, requests_session
from . import AuthMethod
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
                url = 'https://core.bravecollective.net/api'

        if isinstance(client_key, SigningKey):
            priv = client_key
        elif hasattr(client_key, 'read'):
            priv_pem = client_key.read()
            priv = SigningKey.from_pem(priv_pem)
        else:
            with open(client_key, 'r') as f:
                priv_pem = f.read()
                priv = SigningKey.from_pem(priv_pem)

        if isinstance(server_key, VerifyingKey):
            pub = server_key
        elif hasattr(server_key, 'read'):
            pub_pem = server_key.read()
            pub = VerifyingKey.from_pem(pub_pem)
        else:
            with open(server_key, 'r') as f:
                pub_pem = f.read()
                pub = VerifyingKey.from_pem(pub_pem)

        self.api = API(url, identifier, priv, pub,
                requests_session)

    def login(self, form):
        # Redirect to Core for the authorization token. Give URLs to return to.
        # Sidenote: At this time, Brave has nearly 0 API documentation. The
        # kinda-sorta hidden TEST Auth API documentation is more complete.
        result_url = url_for('auth_method_login',
                auth_method=self.__class__.__name__.lower())
        core_url = self.api.core.authorize(success=result_url,
                failure=result_url)
        print(core_url)
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
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                    identity=Identity(user.id))
            # TODO Have a meaningful redirect for this
            return redirect(url_for('index'))
        else:
            flash("Login failed.")
            return redirect(url_for('login'))


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

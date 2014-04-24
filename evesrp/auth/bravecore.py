from ecdsa import SigningKey, VerifyingKey, NIST256p
from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app, request
from hashlib import sha256
from binascii import unhexlify

from .. import db, requests_session
from . import AuthMethod, AuthForm
from .models import User, Group


class BraveCore(AuthMethod):
    name = 'Brave Core'

    def __init__(self, client_key, server_key, identifier,
            url='https://core.braveineve.com'):
        self.api = API(url, identifier, client_key, server_key,
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
                user = CoreUser.query.filter_by(token=token).one()
            except NoResultFound:
                user = CoreUser(name=None, token=token)
                db.session.add(user)
            # update user information
            info = self.api.core.info(token=token)
            user.name = info['character']['name']
            # Sync up group membership
            for tag in info['tags']:
                try:
                    group = CoreGroup.query.filter_by(core_id=tag).one()
                except NoResultFound:
                    group = CoreGroup()
                    group.core_id = tag
                    # TODO: Figure out how to get the Group name
                    db.session.add(group)
                user.groups.append(group)
            for tag in user.groups.difference(info['tags']):
                group = CoreGroup.query.filter_by(core_id=tag).one()
                user.groups.remove(group)
            db.session.commit()
            self.login_user(user)
            # TODO Have a meaningful redirect for this
            return redirect(url_for('index'))
        else:
            flash("Login failed.")
            return redirect(url_for('login.login'))


class CoreUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    token = db.Column(db.String(100))

    @classmethod
    def authmethod(cls):
        return BraveCore


class CoreGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    core_id = db.Column(db.Integer, index=True)
    description = db.Column(db.Text)

    @classmethod
    def authmethod(cls):
        return BraveCore

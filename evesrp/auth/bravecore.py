from ecdsa import SigningKey, VerifyingKey, NIST256p
from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort, current_app, request
from hashlib import sha256
from binascii import unhexlify

from .. import db, requests_session
from . import AuthMethod, AuthForm
from .models import User, Group, Pilot


class BraveCore(AuthMethod):
    def __init__(self, client_key, server_key, identifier,
            url='https://core.braveineve.com', **kwargs):
        self.api = API(url, identifier, client_key, server_key,
                requests_session).api
        if 'name' not in kwargs:
            kwargs['name'] = 'Brave Core'
        super(BraveCore, self).__init__(**kwargs)

    def login(self, form):
        # Redirect to Core for the authorization token. Give URLs to return to.
        # Sidenote: At this time, Brave has nearly 0 API documentation. The
        # kinda-sorta hidden TEST Auth API documentation is more complete.
        result_url = url_for('login.auth_method_login', _external=True,
                auth_method=self.safe_name)
        response = self.api.core.authorize(success=result_url,
                failure=result_url)
        core_url = response['location']
        return redirect(core_url)

    def list_groups(self, user=None):
        pass

    def view(self):
        token = request.args.get('token')
        if token is not None:
            info = self.api.core.info(token=token)
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
            for group_name in info['tags']:
                try:
                    group = CoreGroup.query.filter_by(name=group_name,
                            authmethod=self.name).one()
                except NoResultFound:
                    group = CoreGroup(group_name, self.name)
                    db.session.add(group)
                user.groups.add(group)
            for group in user.groups:
                if group.name not in info['tags']:
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
            # TODO Have a meaningful redirect for this
            return redirect(url_for('index'))
        else:
            flash("Login failed.")
            return redirect(url_for('login.login'))


class CoreUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    token = db.Column(db.String(100))


class CoreGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    description = db.Column(db.Text)

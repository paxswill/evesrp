from brave.api.client import SignedAuth, API
from sqlalchemy.orm.exc import NoResultFound
from flask import flash, url_for, redirect, abort

from .. import db, auth_methods, requests_session
from . import AuthMethod
from .models import User, Group


def brave_login():
    token = request.args.get('token')
    if token is not None:
        try:
            user = BraveCoreUser.query.filter_by(token=token).one()
        except NoResultFound:
            # work back and get the API object
            api = None
            for auth_method in auth_methods:
                if isinstance(auth_method, BraveCore):
                    api = auth_method.api
            if api is None:
                # TODO Handle this possiblity
                pass
            user = BraveCoreUser(token=token)
            db.session.add(user)
        # update user information
        info = api.core.info(token=token)
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
        # TODO Have a meaningful redirect for this
        return redirect(url_for('index'))
    else:
        flash("Login failed.")
        return redirect(url_for('login'))


class BraveCore(AuthMethod):
    name = 'Brave Core'

    def __init__(self, identifier, client_key, server_key,
            url='https://core.bravecollective.net/api'):
        self.api = API(url, identifier, client_key, server_key,
                requests_session)

    def login(self, form):
        # Redirect to Core for the authorization token. Give URLs to return to.
        # Sidenote: At this time, Brave has nearly 0 API documentation. The
        # kinda-sorta hidden TEST Auth API documentation is more complete.
        core_url = self.api.core.authorize(success=url_for('brave_login',
                failure=url_for('brave_login')))
        print(core_url)
        return redirect(core_url)

    @classmethod
    def register_views(cls, app):
        app.add_url_rule('/login/brave', 'brave_login', brave_login)

    def list_groups(self, user=None):
        pass


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

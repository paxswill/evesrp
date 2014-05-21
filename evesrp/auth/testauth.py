import hashlib

from flask import flash, url_for, redirect, abort, request
from sqlalchemy.orm.exc import NoResultFound
from wtforms.fields import StringField, PasswordField, HiddenField, SubmitField
from wtforms.validators import InputRequired

from .. import db, requests_session
from . import AuthMethod, AuthForm
from .models import User, Group, Pilot


class TestLoginForm(AuthForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Log In')


class TestAuth(AuthMethod):
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key
        if 'name' not in kwargs:
            kwargs['name'] = 'Test Auth'
        super(TestAuth, self).__init__(**kwargs)

    def form(self):
        return TestLoginForm

    def login(self, form):
        sha = hashlib.sha1()
        sha.update(form.password.data.encode())
        params = {
                'user': form.username.data,
                'pass': sha.hexdigest()
                }
        response = requests_session.get(
                'https://auth.pleaseignore.com/api/1.0/login',
                params=params)
        json = response.json()

        if json['auth'] == 'failed':
            if json['error'] == 'none':
                flash("User '{}' not found.".format(form.username.data),
                        category='error')
            elif json['error'] == 'multiple':
                flash("Multiple users found.", category='error')
            elif json['error'] == 'password':
                flash("Incorrect password.", category='error')
            return redirect(url_for('login.login'))
        elif json['auth'] == 'ok':
            try:
                user = TestUser.query.filter_by(auth_id=json['id'],
                        authmethod=self.name).one()
            except NoResultFound:
                # Create new User
                user = TestUser(json['username'], json['id'], self.name)
                db.session.add(user)
            # Update values from Auth
            user.admin = json['superuser'] or json['staff'] or \
                    json['username'] in self.admins
            # Sync up group values
            for group in json['groups']:
                try:
                    db_group = TestGroup.query.\
                            filter_by(auth_id=group['id'],
                                    authmethod=self.name).one()
                except NoResultFound:
                    db_group = TestGroup(group['name'], group['id'], self.name)
                    db.session.add(db_group)
                user.groups.add(db_group)
                # TODO: Remove old groups
            # Sync pilot associations
            pilot = Pilot.query.get(json['primarycharacter']['id'])
            if not pilot:
                pilot = Pilot(user, json['primarycharacter']['name'],
                        json['primarycharacter']['id'])
            pilot.user = user
            # Getting all pilots requires an Auth API key.
            if self.api_key:
                resp_user = requests_session.get(
                        'https://auth.pleaseignore.com/api/1.0/user', params=
                        {
                            'userid': user.id,
                            'apikey': self.api_key
                        })
                if resp_user.status_code == 200:
                    for char in resp_user.json()['characters']:
                        try:
                            pilot = Pilot.query.get(char['id'])
                        except NoResultFound:
                            pilot = Pilot(user, char['name'], char['id'])
                        else:
                            pilot.user = user
            # All done
            db.session.commit()
            self.login_user(user)
            return redirect(request.args.get('next') or url_for('index'))
        else:
            # Not sure what you did to get here, but somehow Auth has returned
            # an invalid response.
            abort(403)

    def list_groups(self, user=None):
        """Return a list of groups descriptors.

        If user is None, return _all_ groups. Otherwise, return the groups a
        member is part of.
        """
        if user is None:
            response = requests_session.get(
                    'https://auth.pleaseignore.com/api/1.0/info',
                    params={'request': 'groups'})
            # TODO Handle possible errors
            groups = set()
            for group in response.json():
                group_tuple = (group['name'], cls.__name__)
                groups.add(group_tuple)
            return groups
        else:
            # NOTE: THis might not be a secure/proper check. Test it.
            if user.authmethod() != cls:
                # TODO: Raise an exception here, this is the wrong authmethod
                # for this user.
                return None
            # TODO: Needs an Auth API key passed in somehow
            response = requests_session.get(
                    'https://auth.pleaseignore.com/api/1.0/user',
                    params={'userid': user.auth_id(), 'apikey': self.apikey})
            groups = set()
            for group in response.json()['groups']:
                group_tuple = (group['name'], cls.__name__)
                groups.add(group_tuple)
            return groups


class TestUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    auth_id = db.Column(db.Integer, nullable=False, index=True)

    def __init__(self, username, auth_id, authmethod, groups=None, **kwargs):
        self.name = username
        self.auth_id = auth_id
        self.authmethod = authmethod


class TestGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    auth_id = db.Column(db.Integer, nullable=False, index=True)
    description = db.Column(db.Text)

    def __init__(self, name, auth_id, authmethod):
        self.name = name
        self.auth_id = auth_id
        self.authmethod = authmethod

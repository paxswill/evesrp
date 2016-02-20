from __future__ import absolute_import
import hashlib

from flask import flash, url_for, redirect, abort, request
from flask.ext.wtf import Form
import six
from sqlalchemy.orm.exc import NoResultFound
from wtforms.fields import StringField, PasswordField, HiddenField, SubmitField
from wtforms.validators import InputRequired

from .. import db, requests_session
from ..util import ensure_unicode, is_safe_redirect
from . import AuthMethod
from .models import User, Group, Pilot


class TestAuth(AuthMethod):
    def __init__(self, api_key=None, **kwargs):
        """Authentication method using `TEST Auth
        <https://github.com/nikdoof/test-auth>`_'s legacy (a.k.a v1) API.

        :param str api_key: (optional) An Auth API key. Without this, only
            primary characters are able to be accessed/used.
        :param str name: The user-facing name for this authentication method.
            Default: 'Test Auth'
        """
        self.api_key = api_key
        if 'name' not in kwargs:
            kwargs['name'] = u'Test Auth'
        super(TestAuth, self).__init__(**kwargs)

    def form(self):
        class TestLoginForm(Form):
            username = StringField(u'Username', validators=[InputRequired()])
            password = PasswordField(u'Password', validators=[InputRequired()])
            submit = SubmitField(u'Log In using {}'.format(self.name))
        return TestLoginForm

    def login(self, form):
        sha = hashlib.sha1()
        password = form.password.data
        if isinstance(password, six.text_type):
            password = password.decode('utf-8')
        sha.update(password)
        params = {
                'user': form.username.data,
                'pass': sha.hexdigest()
                }
        response = requests_session.get(
                'https://auth.pleaseignore.com/api/1.0/login',
                params=params)
        json = response.json()
        # JSON is unicode, by definition
        if json[u'auth'] == u'failed':
            if json[u'error'] == u'none':
                flash(u"User '{}' not found.".format(form.username.data),
                        category=u'error')
            elif json[u'error'] == u'multiple':
                flash(u"Multiple users found.", category=u'error')
            elif json[u'error'] == u'password':
                flash(u"Incorrect password.", category=u'error')
            return redirect(url_for('login.login'))
        elif json[u'auth'] == u'ok':
            try:
                user = TestUser.query.filter_by(auth_id=json[u'id'],
                        authmethod=self.name).one()
            except NoResultFound:
                # Create new User
                user = TestUser(json[u'username'], json[u'id'], self.name)
                db.session.add(user)
            # Update values from Auth
            user.admin = json[u'superuser'] or json[u'staff'] or \
                    json[u'username'] in self.admins
            # Sync up group values
            for group in json[u'groups']:
                try:
                    db_group = TestGroup.query.\
                            filter_by(auth_id=group[u'id'],
                                    authmethod=self.name).one()
                except NoResultFound:
                    db_group = TestGroup(group[u'name'], group[u'id'],
                            self.name)
                    db.session.add(db_group)
                user.groups.add(db_group)
                # TODO: Remove old groups
            # Sync pilot associations
            pilot = Pilot.query.get(json[u'primarycharacter'][u'id'])
            if not pilot:
                pilot = Pilot(user, json[u'primarycharacter'][u'name'],
                        json[u'primarycharacter'][u'id'])
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
                    for char in resp_user.json()[u'characters']:
                        try:
                            pilot = Pilot.query.get(char[u'id'])
                        except NoResultFound:
                            pilot = Pilot(user, char[u'name'], char[u'id'])
                        else:
                            pilot.user = user
            # All done
            db.session.commit()
            self.login_user(user)
            # Check that the 'next' parameter is safe
            next_url = request.args.get('next')
            if next_url is not None:
                if not is_safe_redirect(next_url):
                    next_url = None
            return redirect(next_url or url_for('index'))
        else:
            # Not sure what you did to get here, but somehow Auth has returned
            # an invalid response.
            abort(403)


class TestUser(User):

    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    #: The Auth ID number for this user.
    auth_id = db.Column(db.Integer, nullable=False, index=True)

    def __init__(self, username, auth_id, authmethod, groups=None, **kwargs):
        """A user from TEST Auth.

        :param str name: The name of the user.
        :param int auth_id: Auth's ID number for the user.
        :param authmethod: The :py:class:`AuthMethod` that created the user.
        """
        self.name = ensure_unicode(username)
        self.auth_id = auth_id
        self.authmethod = ensure_unicode(authmethod)


class TestGroup(Group):

    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)

    #: The Auth ID number for this group.
    auth_id = db.Column(db.Integer, nullable=False, index=True)

    def __init__(self, name, auth_id, authmethod):
        """A group from TEST Auth.

        :param str name: The name of the group.
        :param int auth_id: Auth's ID number for the group.
        :param authmethod: The :py:class:`AuthMethod` that created the group.
        """
        self.name = ensure_unicode(name)
        self.auth_id = auth_id
        self.authmethod = ensure_unicode(authmethod)

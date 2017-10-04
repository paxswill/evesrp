from __future__ import absolute_import
from __future__ import unicode_literals
from unittest import TestCase
import json
from six.moves.urllib.parse import urlparse
from os import environ as env
import httmock
from httmock import urlmatch
from evesrp import create_app, db, init_app
from evesrp.auth import AuthMethod
from evesrp.auth.models import User
from wtforms.fields import StringField, SubmitField
from sqlalchemy.orm.exc import NoResultFound
from flask import redirect, url_for, request, render_template
from flask_wtf import Form


class TestApp(TestCase):

    def setUp(self):
        config = {
            'SECRET_KEY': 'testing',
            'SRP_USER_AGENT_EMAIL': 'testing@example.com',
            'WTF_CSRF_ENABLED': False,
        }
        # Default to an ephemeral SQLite DB for testing unless given another
        # database to connect to.
        config['SQLALCHEMY_DATABASE_URI'] = env.get('DB', 'sqlite:///')
        self.app = create_app(config)
        db.create_all(app=self.app)

    def tearDown(self):
        db.drop_all(app=self.app)


class NullAuthForm(Form):
    name = StringField()
    submit = SubmitField()


class NullAuth(AuthMethod):
    """A bare-bones AuthMethod that does not do any password checking."""

    def login(self, form):
        """Log in a previously registered user."""
        try:
            user = User.query.filter_by(name=form.name.data,
                    authmethod=self.name).one()
        except NoResultFound:
            return redirect(url_for('login.login'))
        self.login_user(user)
        return redirect(request.args.get('next') or url_for('index'))

    def view(self):
        """Register a User."""
        form = NullAuthForm()
        if form.validate_on_submit():
            user = User.query.filter_by(name=form.name.data,
                    authmethod=self.name).first()
            if user is None:
                user = User(form.name.data, self.name)
                db.session.add(user)
                db.session.commit()
                self.login_user(user)
                return redirect(url_for('index'))
            else:
                abort(400)
        return render_template('form.html', form=form)

    def form(self):
        return NullAuthForm


class TestLogin(TestApp):

    def setUp(self):
        super(TestLogin, self).setUp()
        self.auth_methods = [
                NullAuth(name='Null Auth 1'),
                NullAuth(name='Null Auth 2'),
        ]
        self.app.config['SRP_AUTH_METHODS'] = self.auth_methods
        init_app(self.app)
        self.normal_name = 'Normal User'
        self.admin_name = 'Admin User'
        self.default_authmethod = self.auth_methods[0]
        with self.app.test_request_context():
            db.session.add(User(self.normal_name,
                self.default_authmethod.name))
            admin_user = User(self.admin_name, self.default_authmethod.name)
            admin_user.admin = True
            db.session.add(admin_user)
            db.session.commit()

    def login(self, username=None):
        if username is None:
            username = self.normal_name
        client = self.app.test_client()
        data = {
            'name': username,
            'submit': 'true',
        }
        auth_method = self.auth_methods[0]
        data = {auth_method.safe_name + '-' + field: value for field, value in
                data.items()}
        client.post('/login/', follow_redirects=True, data=data)
        return client

    @property
    def normal_user(self):
        return User.query.filter_by(name=self.normal_name).one()

    @property
    def admin_user(self):
        return User.query.filter_by(name=self.admin_name).one()


def response(*args, **kwargs):
    resp = httmock.response(*args, **kwargs)
    if isinstance(resp._content, str):
        resp._content = resp._content.encode('utf-8')
    return resp


@urlmatch(netloc=r'(.*\.)?zkillboard\.com', path=r'.*37637533.*')
def paxswill_zkillboard(url, request):
    resp = u"""
    [
        {
            "killmail_id": 37637533,
            "killmail_time": "2014-03-20T02:32:00Z",
            "victim": {
                "damage_taken": 25198,
                "ship_type_id": 12017,
                "character_id": 570140137,
                "corporation_id": 1018389948,
                "alliance_id": 498125261,
                "faction_id": 500001
            },
            "solar_system_id": 30001228,
            "zkb": {
                "fittedValue": 264570854.89,
                "hash": "151055c36c2458271928f87242f189ea315e43b3",
                "points": 1,
                "totalValue": 266421715.39,
                "npc": false,
                "solo": false,
                "awox": false,
                "involved": 42
            }
        }
    ]
    """
    return response(content=resp)


@urlmatch(netloc=r'(.*\.)?zkillboard\.com', path=r'.*38862043.*')
def no_alliance_zkillboard(url, request):
    resp = u"""
    [
        {
            "killmail_id": 37637533,
            "killmail_time": "2014-03-20T02:32:00Z",
            "victim": {
                "damage_taken": 25198,
                "ship_type_id": 12017,
                "character_id": 570140137,
                "corporation_id": 1018389948,
                "alliance_id": 498125261,
                "faction_id": 500001
            },
            "solar_system_id": 30001228,
            "zkb": {
                "fittedValue": 264570854.89,
                "hash": "151055c36c2458271928f87242f189ea315e43b3",
                "points": 1,
                "totalValue": 266421715.39,
                "npc": false,
                "solo": false,
                "awox": false,
                "involved": 42
            }
        }
    ]
    """
    return response(content=resp)


_parsed_esi_url = urlparse('https://esi.tech.ccp.is/v1/killmails/30290604/'
                             '787fb3714062f1700560d4a83ce32c67640b1797/')
@urlmatch(scheme=_parsed_esi_url.scheme,
          netloc=_parsed_esi_url.netloc,
          path=_parsed_esi_url.path)
def foxfour_esi(url, request):
    resp = {
        "killmail_id": 30290604,
        "killmail_time": "2013-05-05T18:09:00Z",
        "victim": {
            "damage_taken": 570,
            "ship_type_id": 670,
            "character_id": 92168909,
            "corporation_id": 109299958,
            "alliance_id": 434243723,
        },
        # Skipping the items array as it's not used
        "items": None,
        # Ditto for attackers
        "attackers": None,
        "solar_system_id": 30002062
    }
    return response(content=json.dumps(resp))


all_mocks = (paxswill_zkillboard, no_alliance_zkillboard, foxfour_esi)

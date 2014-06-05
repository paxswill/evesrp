from unittest import TestCase
import json
from urllib.parse import urlparse
from os import environ as env
import httmock
from httmock import urlmatch
from evesrp import create_app, db
from evesrp.auth import AuthMethod, AuthForm
from evesrp.auth.models import User
from wtforms.fields import StringField
from sqlalchemy.orm.exc import NoResultFound
from flask import redirect, url_for, request, render_template


class TestApp(TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.app.config['SECRET_KEY'] = 'testing'
        self.app.config['USER_AGENT_EMAIL'] = 'testing@example.com'
        self.app.config['WTF_CSRF_ENABLED'] = False
        if 'DB' in env:
            # Default is an in-memroy SQLite database
            self.app.config['SQLALCHEMY_DATABASE_URI'] = env['DB']
        db.create_all(app=self.app)

    def tearDown(self):
        db.drop_all(app=self.app)


class NullAuthForm(AuthForm):
    name = StringField()


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
        self.app.config['AUTH_METHODS'] = self.auth_methods
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


@urlmatch(netloc=r'.*\.zkillboard\.com', path=r'.*37637533.*')
def paxswill_zkillboard(url, request):
    resp = [{
        'killID': '37637533',
        'solarSystemID': '30001228',
        'killTime': '2014-03-20 02:32:00',
        'moonID': '0',
        'victim': {
            'shipTypeID': '12017',
            'damageTaken': '25198',
            'factionName': 'Caldari State',
            'factionID': '500001',
            'allianceName': 'Test Alliance Please Ignore',
            'allianceID': '498125261',
            'corporationName': 'Dreddit',
            'corporationID': '1018389948',
            'characterName': 'Paxswill',
            'characterID': '570140137',
            'victim': '',
        },
        'zkb': {
            'totalValue': '273816945.63',
            'points': '22',
            'involved': 42,
        }
    }]
    return response(content=json.dumps(resp))


@urlmatch(netloc=r'.*\.zkillboard\.com', path=r'.*38862043.*')
def no_alliance_zkillboard(url, request):
    resp = [{
        'killID': '38862043',
        'solarSystemID': '30002811',
        'killTime': '2014-05-15 03:11:00',
        'moonID': '0',
        'victim': {
            'shipTypeID': '598',
            'damageTaken': '1507',
            'factionName': '',
            'factionID': '0',
            'allianceName': '',
            'allianceID': '0',
            'corporationName': 'Omega LLC',
            'corporationID': '98070272',
            'characterName': 'Dave Duclas',
            'characterID': '90741463',
            'victim': '',
        },
        'zkb': {
            'totalValue': '10432408.70',
            'points': '8',
            'involved': 1,
        }
    }]
    return response(content=json.dumps(resp))


_parsed_crest_url = urlparse('http://public-crest.eveonline.com/killmails/30290604/'
                             '787fb3714062f1700560d4a83ce32c67640b1797/')
@urlmatch(scheme=_parsed_crest_url.scheme,
          netloc=_parsed_crest_url.netloc,
          path=_parsed_crest_url.path)
def foxfour_crest(url, request):
    resp = {
        'solarSystem': {
            'id': 30002062,
            'name': 'Todifrauan',
        },
        'killTime': '2013.05.05 18:09:00',
        'victim': {
            'alliance': {
                'id': 434243723,
                'name': 'C C P Alliance',
            },
            'character': {
                'id': 92168909,
                'name': 'CCP FoxFour',
            },
            'corporation': {
                'id': 109299958,
                'name': 'C C P',
            },
            'shipType': {
                'id': 670,
                'name': 'Capsule'
            },
        },
    }
    return response(content=json.dumps(resp))


all_mocks = (paxswill_zkillboard, no_alliance_zkillboard, foxfour_crest)

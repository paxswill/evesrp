from __future__ import absolute_import

import datetime as dt
import os

import pytest
from flask import redirect, url_for, request, render_template
from flask_wtf import Form
from sqlalchemy.orm.exc import NoResultFound
from wtforms.fields import StringField, SubmitField
from evesrp import create_app, db
from evesrp.models import Request, AbsoluteModifier
from evesrp.auth import AuthMethod, PermissionType
from evesrp.auth.models import User, Division, Permission, Pilot
from evesrp.util import utc
from evesrp.util.enum import EnumSymbol
from . import mocks


def pytest_make_parametrize_id(val):
    """Hook that pretty-prints IDs for the enumerated types used as parameters
    in fixtures.
    """
    if isinstance(val, EnumSymbol):
        return val.name
    return None


# Local plugin that adds a command line option for running functional tests
# only.

def pytest_addoption(parser):
    parser.addoption('--browser', action='store_true',
                     help="Run only browser-based tests.")


def pytest_runtest_setup(item):
    # browser-based tests will only run if the --browser option is given.
    browser = item.get_marker('browser')
    run_functional = item.config.getoption('--browser')
    if browser is None and run_functional:
        pytest.skip("Only running functional tests")
    elif browser is not None and not run_functional:
        pytest.skip("Not running functional tests")


# NullAuthForm and NullAuth define an AuthMethod that does no actual
# authentication. It's used to test that logging in actually works and that
# functionality that only works for authenticated users also works.
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


@pytest.fixture
def app_config():
    config = {
        'SECRET_KEY': 'testing',
        'SRP_USER_AGENT_EMAIL': 'testing@example.com',
        'WTF_CSRF_ENABLED': False,
        'TESTING': True,
    }
    # Default to an ephemeral SQLite DB for testing unless given another
    # database to connect to.
    config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB', 'sqlite:///')
    auth_methods = [
            NullAuth(name='Null Auth 1'),
            NullAuth(name='Null Auth 2'),
    ]
    config['SRP_AUTH_METHODS'] = auth_methods
    return config


@pytest.fixture
def evesrp_app(app_config):
    app = create_app(app_config)
    db.create_all(app=app)
    # Implicit shared app context for all users of this fixture
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()
    db.drop_all(app=app)


@pytest.fixture
def request_context(evesrp_app):
    request_ctx = evesrp_app.test_request_context()
    request_ctx.push()
    yield request_ctx
    request_ctx.pop()


@pytest.fixture
def test_client(evesrp_app):
    return evesrp_app.test_client()


# Tests modules that are admin-only should override this fixture
@pytest.fixture(params=['Normal', 'Admin'])
def user_role(request):
    return request.param


@pytest.fixture
def authmethod(evesrp_app):
    return evesrp_app.config['SRP_AUTH_METHODS'][0]


def create_user(name, app, authmethod, is_admin=False):
    user = User(name, authmethod.name)
    user.admin = is_admin
    db.session.add(user)
    db.session.commit()
    return user


# Some tests require having two distinct users. `user` and `other_user`
# guarantee that there will be different users.
@pytest.fixture
def user(evesrp_app, authmethod, user_role):
    username = user_role + ' User'
    is_admin = user_role == 'Admin'
    return create_user(username, evesrp_app, authmethod, is_admin)


@pytest.fixture
def other_user(evesrp_app, authmethod, user_role):
    username = 'Other ' + user_role + ' User'
    is_admin = user_role == 'Admin'
    return create_user(username, evesrp_app, authmethod, is_admin)


def _user_login(user, evesrp_app, authmethod):
    client = evesrp_app.test_client()
    data = {
        'name': user.name,
        'submit': 'true',
    }
    # Munge the paremeter names for the authmethod
    data = {authmethod.safe_name + '-' + field: value for field, value in
            data.items()}
    client.post('/login/', follow_redirects=True, data=data)
    return client

@pytest.fixture
def get_login(evesrp_app, authmethod):
    def _get_login(a_user):
        return _user_login(a_user, evesrp_app, authmethod)
    return _get_login


@pytest.fixture
def user_login(user, get_login):
    # TODO: Raise deprecation warning in favor of get_login
    return get_login(user)


@pytest.fixture
def other_user_login(other_user, get_login):
    # TODO: Raise deprecation warning in favor of get_login
    return get_login(other_user)


@pytest.fixture
def crest():
    return mocks.crest


@pytest.fixture
def zkillboard():
    return mocks.zKillboard


@pytest.fixture
def srp_request(user, other_user):
    mock_killmail = dict(
            id=12842852,
            type_name='Erebus',
            type_id=671,
            corporation='Ever Flow',
            corporation_id=1991488321,
            alliance='Northern Coalition.',
            alliance_id=1727758877,
            killmail_url='http://eve-kill.net/?a=kill_detail&kll_id=12842852',
            base_payout=73957900000,
            kill_timestamp=dt.datetime(2012, 3, 25, 0, 44, 0, tzinfo=utc),
            system='92D-OI',
            system_id=30001312,
            constellation='XHYS-O',
            constellation_id=20000191,
            region='Venal',
            region_id=10000015,
            pilot_id=133741,
    )
    division = Division('Testing Disivion')
    # SQLAlchemy magic is adding these to the database session
    Pilot(user, 'eLusi0n', mock_killmail['pilot_id'])
    srp_request = Request(user, 'Original details', division,
                          mock_killmail.items())
    Permission(division, PermissionType.review, other_user)
    Permission(division, PermissionType.pay, other_user)
    # Modifier used by some tests.
    AbsoluteModifier(srp_request, other_user, 'Absolute Fixture Modifier', 10)
    db.session.commit()
    return srp_request

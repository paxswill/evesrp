from __future__ import absolute_import

import datetime as dt
from os import environ as env

import pytest
from flask import redirect, url_for, request, render_template
from flask_wtf import Form
from wtforms.fields import StringField, SubmitField
from evesrp import create_app, db
from evesrp.models import Request, AbsoluteModifier
from evesrp.auth import AuthMethod, PermissionType
from evesrp.auth.models import User, Division, Permission, Pilot
from evesrp.util import utc
from . import mocks


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
    }
    # Default to an ephemeral SQLite DB for testing unless given another
    # database to connect to.
    config['SQLALCHEMY_DATABASE_URI'] = env.get('DB', 'sqlite:///')
    auth_methods = [
            NullAuth(name='Null Auth 1'),
            NullAuth(name='Null Auth 2'),
    ]
    config['SRP_AUTH_METHODS'] = auth_methods
    return config


@pytest.yield_fixture
def evesrp_app(app_config):
    app = create_app(app_config)
    # Implicit shared app context for all users of this fixture
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield app
    db.drop_all()
    ctx.pop()



# Tests modules that are admin-only should override this fixture
@pytest.fixture(params=['Normal', 'Admin'])
def user_role(request):
    return request.param


def create_user(name, app, is_admin=False):
    # TODO Parameterize with auth method is ebing used?
    auth_method = app.config['SRP_AUTH_METHODS'][0]
    user = User(name, auth_method.name)
    user.admin = is_admin
    db.session.add(user)
    db.session.commit()
    return user


# Some tests require having two distinct users. `user` and `other_user`
# guarantee that there will be different users.
@pytest.fixture
def user(evesrp_app, user_role):
    username = user_role + ' User'
    is_admin = user_role == 'Admin'
    return create_user(username, evesrp_app, is_admin)


@pytest.fixture
def other_user(evesrp_app, user_role):
    username = 'Other ' + user_role + ' User'
    is_admin = user_role == 'Admin'
    return create_user(username, evesrp_app, is_admin)



def _user_login(user, evesrp_app):
    client = evesrp_app.test_client()
    data = {
        'name': user.name,
        'submit': 'true',
    }
    # TODO Parameterize with auth method is ebing used?
    auth_method = evesrp_app.config['SRP_AUTH_METHODS'][0]
    # Munge the paremeter names for the authmethod
    data = {auth_method.safe_name + '-' + field: value for field, value in
            data.items()}
    client.post('/login/', follow_redirects=True, data=data)
    return client


@pytest.fixture
def user_login(user, evesrp_app):
    return _user_login(user, evesrp_app)


@pytest.fixture
def other_user_login(other_user, evesrp_app):
    return _user_login(other_user, evesrp_app)


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

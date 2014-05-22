from ..util import TestApp
from evesrp import db
from evesrp.auth import AuthMethod, AuthForm
from evesrp.auth.models import User
from wtforms.fields import StringField
from sqlalchemy.orm.exc import NoResultFound
from flask import redirect, url_for, request, render_template


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
        return render_template('form.html', form=form)

    def form(self):
        return NullAuthForm


class TestNullAuth(TestApp):

    def setUp(self):
        super(TestNullAuth, self).setUp()
        self.auth_methods = [
                NullAuth(name='Null Auth 1'),
                NullAuth(name='Null Auth 2'),
        ]
        self.app.config['AUTH_METHODS'] = self.auth_methods

class TestTrampolineView(TestNullAuth):

    def test_account_creation(self):
        """Tests that the AuthMethod-specific views are being rendered
        properly, including for POST requests.
        """
        with self.app.test_client() as c:
            # Actual request
            resp = c.post('/login/null_auth_1/', follow_redirects=True, data={
                'name': 'Normal User',
                'submit': 'true',
            })
            self.assertIn(b'Log Out', resp.data)
            self.assertIsNotNone(User.query.filter_by(name='Normal User')
                    .first())


class TestLogin(TestNullAuth):

    def setUp(self):
        super(TestLogin, self).setUp()
        with self.app.test_request_context():
            db.session.add(User('Testing', self.auth_methods[0].name))
            db.session.commit()

    def test_login(self):
        client = self.app.test_client()
        data = {
            'name': 'Testing',
            'submit': 'true',
        }
        auth_method = self.auth_methods[0]
        data = {auth_method.safe_name + '-' + field: value for field, value in
                data.items()}
        resp = client.post('/login/', follow_redirects=True, data=data)
        self.assertIn(b'Log Out', resp.data)
        # For other tests depending on logging in
        return client

    def test_logout(self):
        # Get a test client that's logged in
        client = self.test_login()
        resp = client.get('/logout/', follow_redirects=True)
        self.assertIn(b'Log In', resp.data)


class TestMethodTabs(TestNullAuth):

    def test_single_auth_method(self):
        # Remove the second auth method
        self.app.config['AUTH_METHODS'].pop()
        # Test
        resp = self.app.test_client().get('/login', follow_redirects=True)
        self.assertIn(b'Null Auth 1', resp.data)
        self.assertNotIn(b'Null Auth 2', resp.data)

    def test_multiple_auth_methods(self):
        resp = self.app.test_client().get('/login', follow_redirects=True)
        self.assertIn(b'Null Auth 1', resp.data)
        self.assertIn(b'Null Auth 2', resp.data)

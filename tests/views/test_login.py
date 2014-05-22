from ..util import TestApp, TestLogin
from evesrp import db
from evesrp.auth import AuthMethod, AuthForm
from evesrp.auth.models import User


class TestTrampolineView(TestLogin):

    def test_account_creation(self):
        """Tests that the AuthMethod-specific views are being rendered
        properly, including for POST requests.
        """
        with self.app.test_client() as c:
            # Actual request
            resp = c.post('/login/null_auth_1/', follow_redirects=True, data={
                'name': 'Unique User',
                'submit': 'true',
            })
            self.assertIn('Log Out', resp.get_data(as_text=True))
            self.assertIsNotNone(User.query.filter_by(name='Normal User')
                    .first())


class TestLoginView(TestLogin):

    def setUp(self):
        super(TestLoginView, self).setUp()
        with self.app.test_request_context():
            db.session.add(User('Testing', self.auth_methods[0].name))
            db.session.commit()

    def test_login(self, username='Testing'):
        client = self.app.test_client()
        data = {
            'name': username,
            'submit': 'true',
        }
        auth_method = self.auth_methods[0]
        data = {auth_method.safe_name + '-' + field: value for field, value in
                data.items()}
        resp = client.post('/login/', follow_redirects=True, data=data)
        self.assertIn('Log Out', resp.get_data(as_text=True))

    def test_logout(self):
        # Get a test client that's logged in
        client = self.login()
        resp = client.get('/logout/', follow_redirects=True)
        self.assertIn('Log In', resp.get_data(as_text=True))


class TestMethodTabs(TestLogin):

    def test_single_auth_method(self):
        # Remove the second auth method
        self.app.config['AUTH_METHODS'].pop()
        # Test
        resp = self.app.test_client().get('/login', follow_redirects=True)
        self.assertIn('Null Auth 1', resp.get_data(as_text=True))
        self.assertNotIn('Null Auth 2', resp.get_data(as_text=True))

    def test_multiple_auth_methods(self):
        resp = self.app.test_client().get('/login', follow_redirects=True)
        self.assertIn('Null Auth 1', resp.get_data(as_text=True))
        self.assertIn('Null Auth 2', resp.get_data(as_text=True))

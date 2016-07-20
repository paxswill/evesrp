from __future__ import absolute_import
import pytest


def test_authmethod_trampoline_views(evesrp_app, test_client):
    """Tests that the AuthMethod-specific views are being rendered
    properly, including for POST requests. In this case, NullAuth has a custom
    view that creates users.
    """
    with test_client as c:
        # Actual request
        resp = c.post('/login/null_auth_1/', follow_redirects=True, data={
            'name': 'Unique User',
            'submit': 'true',
        })
        assert 'Log Out' in resp.get_data(as_text=True)


def test_login(user_login):
    # user_login already does what we want, just test it
    resp = user_login.get('/', follow_redirects=True)
    assert 'Log Out' in resp.get_data(as_text=True)


def test_logout(user_login):
    resp = user_login.get('/logout/', follow_redirects=True)
    assert 'Log In' in resp.get_data(as_text=True)


class TestSingleTabs(object):

    @pytest.fixture
    def app_config(self, app_config):
        app_config['SRP_AUTH_METHODS'].pop()
        return app_config

    def test_single_auth_method(self, test_client):
        resp = test_client.get('/login', follow_redirects=True)
        assert 'Null Auth 1' in resp.get_data(as_text=True)
        assert 'Null Auth 2' not in resp.get_data(as_text=True)

def test_multiple_auth_methods(test_client):
    resp = test_client.get('/login', follow_redirects=True)
    assert 'Null Auth 1' in resp.get_data(as_text=True)
    assert 'Null Auth 2' in resp.get_data(as_text=True)

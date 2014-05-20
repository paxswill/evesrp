from ..util import TestApp
from evesrp import create_app, db
from evesrp.views import index
from evesrp.auth.models import User


class TestIndexRedirect(TestApp):

    def test_anonymous_user(self):
        resp = self.app.test_client().get('/')
        self.assertTrue(resp.status_code, 302)
        self.assertIn('/login/', resp.headers['Location'])

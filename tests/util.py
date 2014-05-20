from unittest import TestCase
from evesrp import create_app, db


class TestApp(TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.app.config['SECRET_KEY'] = 'testing'
        self.app.config['USER_AGENT_EMAIL'] = 'testing@example.com'
        db.create_all(app=self.app)

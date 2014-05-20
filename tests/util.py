from unittest import TestCase
from evesrp import create_app, db


class TestApp(TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        db.create_all(app=self.app)

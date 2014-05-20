from unittest import TestCase
from evesrp import create_app, db
from evesrp.auth.models import Entity, User, Group, Permission, Division,\
        Note, Pilot


class TestApp(TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        db.create_all(app=self.app)


class TestGroups(TestApp):

    def setUp(self):
        super(TestGroups, self).setUp()
        with self.app.test_request_context():
            u1 = User('User One', id=1)
            u2 = User('User Two', id=2)
            u3 = User('User Three', id=3)
            u4 = User('User Four', id=4)
            g1 = Group('Group One', id=10)
            g2 = Group('Group Two', id=20)
            db.session.add_all((u1, u2, u3, u4, g1, g2))
            # Users 1 and 2 belong to Groups 1 and 2. User 3 belongs to both,
            # User 4 belongs to no groups
            g1.users.add(u1)
            g2.users.add(u2)
            g1.users.add(u3)
            g2.users.add(u3)
            db.session.commit()

    def test_group_membership(self):
        with self.app.test_request_context():
            self.assertIn(
                    User.query.get(1),
                    Group.query.get(10).users)
            self.assertNotIn(
                    User.query.get(1),
                    Group.query.get(20).users)
            self.assertIn(
                    User.query.get(2),
                    Group.query.get(20).users)
            self.assertNotIn(
                    User.query.get(2),
                    Group.query.get(10).users)
            self.assertIn(
                    User.query.get(3),
                    Group.query.get(10).users)
            self.assertIn(
                    User.query.get(3),
                    Group.query.get(20).users)
            self.assertNotIn(
                    User.query.get(4),
                    Group.query.get(10).users)
            self.assertNotIn(
                    User.query.get(4),
                    Group.query.get(20).users)

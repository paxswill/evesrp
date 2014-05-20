from unittest import TestCase
from evesrp import create_app, db
from evesrp.auth.models import Entity, User, Group, Permission, Division


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


class TestPermissions(TestGroups):

    def setUp(self):
        super(TestPermissions, self).setUp()
        with self.app.test_request_context():
            # Get the entities
            u1 = User.query.get(1)
            u2 = User.query.get(2)
            u3 = User.query.get(3)
            u4 = User.query.get(4)
            g1 = Group.query.get(10)
            g2 = Group.query.get(20)
            # Three Divisions, Even, Odd, and Prime
            even = Division('Even')
            odd = Division('Odd')
            prime = Division('Prime')
            db.session.add_all((even, odd, prime))
            # Grant 'submit' for the even, odd and prime groups to the
            # individual users (except user 4)
            Permission(odd, 'submit', u1)
            Permission(even, 'submit', u2)
            Permission(odd, 'submit', u3)
            Permission(prime, 'submit', u2)
            Permission(prime, 'submit', u3)
            # Grant 'review' for odd to group 1
            Permission(odd, 'review', g1)
            # Grant 'pay' to user 4 for prime and to user 3 for even
            Permission(even, 'pay', u3)
            Permission(prime, 'pay', u4)
            # In summary:
            # User 1 can submit to odd, and review odd (through Group 1)
            # User 2 can submit to even and prime
            # User 3 can submit to odd and prime, review odd (through Group
            # 1), and pay out even
            # User 4 can pay out prime
            db.session.commit()

    def test_basic_has_permission(self):
        with self.app.test_request_context():
            # Get users
            u1 = User.query.get(1)
            u2 = User.query.get(2)
            u3 = User.query.get(3)
            u4 = User.query.get(4)
            # Actual tests
            self.assertTrue(u1.has_permission('submit'))
            self.assertTrue(u1.has_permission('review'))
            self.assertFalse(u1.has_permission('pay'))

            self.assertTrue(u2.has_permission('submit'))
            self.assertFalse(u2.has_permission('review'))
            self.assertFalse(u2.has_permission('pay'))

            self.assertTrue(u3.has_permission('submit'))
            self.assertTrue(u3.has_permission('review'))
            self.assertTrue(u3.has_permission('pay'))

            self.assertFalse(u4.has_permission('submit'))
            self.assertFalse(u4.has_permission('review'))
            self.assertTrue(u4.has_permission('pay'))

    def test_has_permission_in_division(self):
        with self.app.test_request_context():
            # Get users
            u1 = User.query.get(1)
            u2 = User.query.get(2)
            u3 = User.query.get(3)
            u4 = User.query.get(4)
            odd = Division.query.filter_by(name='Odd').one()
            even = Division.query.filter_by(name='Even').one()
            prime = Division.query.filter_by(name='Prime').one()
            # Tests
            users = (u1, u2, u3, u4)
            divisions = (odd, even, prime)
            permissions = ('submit', 'review', 'pay')
            passing = {
                u1: {
                    odd: ('submit', 'review'),
                },
                u2: {
                    even: ('submit',),
                    prime: ('submit',),
                },
                u3: {
                    odd: ('submit', 'review'),
                    even: ('pay',),
                    prime: ('submit',),
                },
                u4: {
                    prime: ('pay',),
                },
            }
            for user in users:
                # every user has an entry in passing, so don't bother checking
                # for existence
                passing_divisions = passing[user]
                false_negative = ''.join(("{user.name} does have {perm} "
                                          " in {div.name}."))
                false_positive = ''.join(("{user.name} does not have "
                                          "{perm} in {div.name}."))
                for division in divisions:
                    # If a division isn't present, the user has no permissions
                    # for it.
                    passing_permissions = passing_divisions.get(division)
                    for permission in permissions:
                        if passing_permissions is None \
                                or permission not in passing_permissions:
                            self.assertFalse(
                                    user.has_permission(permission, division),
                                    msg=false_negative.format(
                                            user=user,
                                            perm=permission,
                                            div=division))
                        else:
                            self.assertTrue(
                                    user.has_permission(permission, division),
                                    msg=false_positive.format(
                                            user=user,
                                            perm=permission,
                                            div=division))

    def test_division_permissions(self):
        with self.app.test_request_context():
            # Get users and divisions
            odd = Division.query.filter_by(name='Odd').one().permissions
            even = Division.query.filter_by(name='Even').one().permissions
            prime = Division.query.filter_by(name='Prime').one().permissions
            # Tests
            self.assertEqual(len(odd['submit']), 2)
            self.assertEqual(len(odd['review']), 1)
            self.assertEqual(len(odd['pay']), 0)

            self.assertEqual(len(even['submit']), 1)
            self.assertEqual(len(even['review']), 0)
            self.assertEqual(len(even['pay']), 1)

            self.assertEqual(len(prime['submit']), 2)
            self.assertEqual(len(prime['review']), 0)
            self.assertEqual(len(prime['pay']), 1)

from ..util import TestLogin
from evesrp import db
from evesrp.auth.models import User, Group, Division, Permission
from evesrp.transformers import ShipTransformer


class TestAddDivision(TestLogin):

    def test_add_division(self):
        client = self.login(self.admin_name)
        resp = client.post('/divisions/add/', follow_redirects=True,
                data={'name': 'Test Division'})
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            divisions = Division.query.all()
            self.assertEqual(len(divisions), 1)
            self.assertEqual(divisions[0].name, 'Test Division')


class TestListDivisions(TestLogin):

    def setUp(self):
        super(TestListDivisions, self).setUp()
        with self.app.test_request_context():
            divisions = [
                Division('Division One'),
                Division('Division Two'),
                Division('Division Three'),
            ]
            db.session.add_all(divisions)
            db.session.commit()

    def test_list_divisions(self):
        client = self.login(self.admin_name)
        resp = client.get('/divisions/', follow_redirects=True)
        self.assertIn(b'Division One', resp.data)
        self.assertIn(b'Division Two', resp.data)
        self.assertIn(b'Division Three', resp.data)


class TestDivisionDetails(TestLogin):

    def setUp(self):
        super(TestDivisionDetails, self).setUp()
        with self.app.test_request_context():
            db.session.add(Division('Test Division'))
            db.session.add(Group('Group 1', self.default_authmethod.name,
                    id=10))
            db.session.commit()
        self.app.config['SRP_SHIP_URL_TRANSFORMERS'] = [
            ShipTransformer('Test Transformer', '')
        ]

    def test_add_entity_by_id(self):
        client = self.login(self.admin_name)
        resp = client.post('/divisions/1/', follow_redirects=True, data={
                'action': 'add',
                'permission': 'submit',
                'id_': 10,
                'form_id': 'entity',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Group 1', resp.data)
        with self.app.test_request_context():
            self.assertIsNotNone(Permission.query.filter_by(division_id=1,
                    entity_id=10, permission='submit').first())

    def test_add_entity_by_name(self):
        client = self.login(self.admin_name)
        resp = client.post('/divisions/1/', follow_redirects=True, data={
                'action': 'add',
                'permission': 'submit',
                'name': 'Group 1',
                'form_id': 'entity',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Group 1', resp.data)
        with self.app.test_request_context():
            self.assertIsNotNone(Permission.query.filter_by(division_id=1,
                    entity_id=10, permission='submit').first())

    def test_set_url_transformer(self):
        client = self.login(self.admin_name)
        resp = client.post('/divisions/1/', follow_redirects=True, data={
                'name': 'Test Transformer',
                'kind': 'ship',
                'form_id': 'transformer',
        })
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            division = Division.query.get(1)
            self.assertEqual(division.ship_transformer,
                    self.app.config['SRP_SHIP_URL_TRANSFORMERS'][0])

    def test_unset_url_transformer(self):
        client = self.login(self.admin_name)
        with self.app.test_request_context():
            division = Division.query.get(1)
            division.ship_transformer = \
                    self.app.config['SRP_SHIP_URL_TRANSFORMERS'][0]
            db.session.commit()
        resp = client.post('/divisions/1/', follow_redirects=True, data={
                'name': 'none',
                'kind': 'ship',
                'form_id': 'transformer',
        })
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            division = Division.query.get(1)
            self.assertIsNone(division.ship_transformer)

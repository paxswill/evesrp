from __future__ import absolute_import
from __future__ import unicode_literals
from ..util_tests import TestLogin
import evesrp
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import User, Group, Division, Permission
from evesrp.transformers import Transformer


class TestAddDivision(TestLogin):

    def test_add_division(self):
        client = self.login(self.admin_name)
        resp = client.post('/division/add/', follow_redirects=True,
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
        resp = client.get('/division/', follow_redirects=True)
        self.assertIn('Division One', resp.get_data(as_text=True))
        self.assertIn('Division Two', resp.get_data(as_text=True))
        self.assertIn('Division Three', resp.get_data(as_text=True))


class TestDivisionDetails(TestLogin):

    def setUp(self):
        super(TestDivisionDetails, self).setUp()
        with self.app.test_request_context():
            db.session.add(Division('Test Division'))
            db.session.add(Group('Group 1', self.default_authmethod.name,
                    id=10))
            db.session.commit()
        self.app.config['SRP_SHIP_TYPE_URL_TRANSFORMERS'] = [
            ('Test Transformer', ''),
        ]
        evesrp.init_app(self.app)

    def test_add_entity_by_id(self):
        client = self.login(self.admin_name)
        resp = client.post('/division/1/', follow_redirects=True, data={
                'action': 'add',
                'permission': 'submit',
                'id_': 10,
                'form_id': 'entity',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Group 1', resp.get_data(as_text=True))
        with self.app.test_request_context():
            self.assertIsNotNone(Permission.query.filter_by(division_id=1,
                    entity_id=10, permission=PermissionType.submit).first())

    def test_add_entity_by_name(self):
        client = self.login(self.admin_name)
        resp = client.post('/division/1/', follow_redirects=True, data={
                'action': 'add',
                'permission': 'submit',
                'name': 'Group 1',
                'form_id': 'entity',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Group 1', resp.get_data(as_text=True))
        with self.app.test_request_context():
            self.assertIsNotNone(Permission.query.filter_by(division_id=1,
                    entity_id=10, permission=PermissionType.submit).first())

    def test_set_url_transformer(self):
        client = self.login(self.admin_name)
        resp = client.post('/division/1/', follow_redirects=True, data={
                'transformer': 'Test Transformer',
                'attribute': 'ship_type',
                'form_id': 'transformer',
        })
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            division = Division.query.get(1)
            self.assertEqual(division.transformers['ship_type'],
                    self.app.url_transformers['ship_type']['Test Transformer'])

    def test_unset_url_transformer(self):
        client = self.login(self.admin_name)
        with self.app.test_request_context():
            division = Division.query.get(1)
            division.ship_transformer = \
                    self.app.url_transformers['ship_type']['Test Transformer']
            db.session.commit()
        resp = client.post('/division/1/', follow_redirects=True, data={
                'transformer': 'none',
                'attribute': 'ship_type',
                'form_id': 'transformer',
        })
        self.assertEqual(resp.status_code, 200)
        with self.app.test_request_context():
            division = Division.query.get(1)
            self.assertIsNone(division.transformers.get('ship_type', None))

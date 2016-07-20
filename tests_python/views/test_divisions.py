from __future__ import absolute_import
import pytest
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import Group, Division, Permission
from evesrp.transformers import Transformer


def test_add_division(evesrp_app, user_role, user_login):
    divisions = Division.query.all()
    assert len(divisions) == 0
    resp = user_login.post('/division/add/', follow_redirects=True,
            data={'name': 'Test Division'})
    if user_role == 'Admin':
        assert resp.status_code == 200
        divisions = Division.query.all()
        assert len(divisions) == 1
        assert divisions[0].name == 'Test Division'
    else:
        assert resp.status_code == 403


@pytest.fixture
def divisions_listing(evesrp_app):
    # Set up divisions to list
    divisions = [
        Division('Division One'),
        Division('Division Two'),
        Division('Division Three'),
    ]
    db.session.add_all(divisions)
    db.session.commit()


def test_list_divisions(evesrp_app, divisions_listing, user_role, user_login):
    resp = user_login.get('/division/', follow_redirects=True)
    if user_role == 'Admin':
        assert 'Division One' in resp.get_data(as_text=True)
        assert 'Division Two' in resp.get_data(as_text=True)
        assert 'Division Three' in resp.get_data(as_text=True)
    else:
        assert 'Division One' not in resp.get_data(as_text=True)
        assert 'Division Two' not in resp.get_data(as_text=True)
        assert 'Division Three' not in resp.get_data(as_text=True)




class TestDivisionDetails(object):

    @pytest.fixture
    def app_config(self, app_config):
        app_config['SRP_TYPE_NAME_URL_TRANSFORMERS'] = [
            ('Test Transformer', ''),
        ]
        return app_config


    @pytest.fixture(autouse=True)
    def division(self, evesrp_app, authmethod):
        self.division = Division('Test Division')
        db.session.add(self.division)
        self.group = Group('Group 1', authmethod.name)
        db.session.add(self.group)
        db.session.commit()

    def _test_entity_add(self, resp, user_role):
        if user_role == 'Admin':
            assert resp.status_code == 200
            assert 'Group 1' in resp.get_data(as_text=True)
            submit_permission = Permission.query.filter_by(
                division_id=self.division.id, entity_id=self.group.id,
                permission=PermissionType.submit).first()
            assert submit_permission is not None
        else:
            assert resp.status_code == 403

    def test_add_entity_by_id(self, user_role, user_login):
        resp = user_login.post('/division/{}/'.format(self.division.id),
                               follow_redirects=True, data={
                                   'action': 'add',
                                   'permission': 'submit',
                                   'id_': self.group.id,
                                   'form_id': 'entity',
                               })
        self._test_entity_add(resp, user_role)

    def test_add_entity_by_name(self, user_role, user_login):
        resp = user_login.post('/division/{}/'.format(self.division.id),
                               follow_redirects=True, data={
                                   'action': 'add',
                                   'permission': 'submit',
                                   'name': self.group.name,
                                   'form_id': 'entity',
                               })
        self._test_entity_add(resp, user_role)

    def test_set_url_transformer(self, evesrp_app, user_role, user_login):
        resp = user_login.post('/division/{}/'.format(self.division.id),
                               follow_redirects=True, data={
                                   'transformer': 'Test Transformer',
                                   'attribute': 'type_name',
                                   'form_id': 'transformer',
                               })
        if user_role == 'Admin':
            assert resp.status_code == 200
            division_transformer = self.division.transformers['type_name']
            app_transformer = \
                evesrp_app.url_transformers['type_name']['Test Transformer']
            assert division_transformer == app_transformer
        else:
            assert resp.status_code == 403

    def test_unset_url_transformer(self, evesrp_app, user_role, user_login):
        # Set the transformer
        self.division.ship_transformer = \
                evesrp_app.url_transformers['type_name']['Test Transformer']
        db.session.commit()
        resp = user_login.post('/division/{}/'.format(self.division.id),
                               follow_redirects=True, data={
                                   'transformer': 'none',
                                   'attribute': 'type_name',
                                   'form_id': 'transformer',
                               })
        if user_role == 'Admin':
            assert resp.status_code == 200
            assert self.division.transformers.get('type_name', None) is None
        else:
            assert resp.status_code == 403

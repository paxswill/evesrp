from __future__ import absolute_import
from __future__ import unicode_literals
import re
from httmock import HTTMock
from evesrp import db
from evesrp.models import Request
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp import views
from ...util import TestLogin, all_mocks


class TestSubmitRequest(TestLogin):

    def setUp(self):
        super(TestSubmitRequest, self).setUp()
        # Setup a bunch of divisions with varying permissions
        with self.app.test_request_context():
            d1 = Division('Division 1')
            d2 = Division('Division 2')
            d3 = Division('Division 3')
            d4 = Division('Division 4')
            d5 = Division('Division 5')
            d6 = Division('Division 6')
            user = self.normal_user
            db.session.add_all((d1, d2, d3, d4, d5, d6))
            # D1: submit, review
            # D2: review
            # D3: submit
            # D4: review, pay
            # D5: pay
            # D6: none
            db.session.add(Permission(d1, PermissionType.submit, user))
            db.session.add(Permission(d1, PermissionType.review, user))
            db.session.add(Permission(d2, PermissionType.review, user))
            db.session.add(Permission(d3, PermissionType.submit, user))
            db.session.add(Permission(d4, PermissionType.review, user))
            db.session.add(Permission(d4, PermissionType.pay, user))
            db.session.add(Permission(d5, PermissionType.pay, user))
            db.session.commit()
        # Python 3 and Python 2.7 have different names for the same method
        try:
            self.assertCountEqual = self.assertItemsEqual
        except AttributeError:
            pass

    def test_division_listing(self):
        client = self.login()
        resp = client.get('/request/add/')
        matches = re.findall(r'<option.*?>(?P<name>[\w\s]+)</option>',
                resp.get_data(as_text=True))
        self.assertEqual(len(matches), 2)
        self.assertCountEqual(matches, ('Division 1', 'Division 3'))

    def test_submit_divisions(self):
        client = self.login()
        with self.app.test_request_context():
            user = self.normal_user
            divisions = user.submit_divisions()
            division_names = [d[1] for d in divisions]
            self.assertEqual(len(division_names), 2)
            self.assertCountEqual(division_names, ('Division 1', 'Division 3'))

    def test_killmail_validation(self):
        # Need to be logged in so validation of permissions works.
        client = self.login()
        with client:
            client.get('/request/add/')
            # RequestsForm needs a list of divisions
            user = self.normal_user
            divisions = user.submit_divisions()
            # Tests
            # ZKillboard
            division = Division.query.filter_by(name='Division 1').one()
            zkb_form = views.requests.RequestForm(
                    url='https://zkillboard.com/kill/37637533/',
                    details='Foo',
                    division=division.id,
                    submit=True)
            zkb_form.division.choices = divisions
            # Fool InputRequired
            zkb_form.details.raw_data = zkb_form.details.data
            with HTTMock(*all_mocks):
                self.assertTrue(zkb_form.validate())
            # CREST
            crest_form = views.requests.RequestForm(
                    url=('http://public-crest.eveonline.com/killmails/'
                         '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'),
                    details='Foo',
                    division=division.id,
                    submit=True)
            crest_form.division.choices = divisions
            crest_form.details.raw_data = crest_form.details.data
            with HTTMock(*all_mocks):
                self.assertTrue(crest_form.validate())
            fail_form = views.requests.RequestForm(
                    url='http://google.com',
                    details='Foo',
                    division=division.id,
                    submit=True)
            fail_form.division.choices = divisions
            fail_form.details.raw_data = fail_form.details.data
            self.assertFalse(fail_form.validate())

    def test_submit_killmail(self):
        with self.app.test_request_context():
            user = self.normal_user
            pilot = Pilot(user, 'Paxswill', 570140137)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        with HTTMock(*all_mocks):
            resp = client.post('/request/add/', follow_redirects=True,
                    data=dict(
                        url='https://zkillboard.com/kill/37637533/',
                        details='Foo',
                        division=division.id,
                        submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('37637533', resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(37637533)
            self.assertIsNotNone(request)

    def test_submit_non_personal_killmail(self):
        with self.app.test_request_context():
            user = self.normal_user
            pilot = Pilot(user, 'The Mittani', 443630591)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        with HTTMock(*all_mocks):
            resp = client.post('/request/add/', follow_redirects=True,
                    data=dict(
                            url='https://zkillboard.com/kill/37637533/',
                            details='Foo',
                            division=division.id,
                            submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can only submit killmails of characters you',
                resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(37637533)
            self.assertIsNone(request)

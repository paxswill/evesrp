import re
from ..util import TestLogin
from evesrp import db
from evesrp.models import Request, Action, Modifier
from evesrp.auth.models import User, Pilot, Division, Permission
from evesrp import views
from wtforms.validators import StopValidation, ValidationError


class TestRequest(TestLogin):

    def setUp(self):
        super(TestRequest, self).setUp()
        with self.app.test_request_context():
            db.session.add(Division('Test Division'))
            db.session.commit()


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
            user = User.query.filter_by(name=self.normal_name).one()
            db.session.add_all((d1, d2, d3, d4, d5, d6))
            # D1: submit, review
            # D2: review
            # D3: submit
            # D4: review, pay
            # D5: pay
            # D6: none
            db.session.add(Permission(d1, 'submit', user))
            db.session.add(Permission(d1, 'review', user))
            db.session.add(Permission(d2, 'review', user))
            db.session.add(Permission(d3, 'submit', user))
            db.session.add(Permission(d4, 'review', user))
            db.session.add(Permission(d4, 'pay', user))
            db.session.add(Permission(d5, 'pay', user))
            db.session.commit()
        # Python 3 and Python 2.7 have different names for the same method
        try:
            self.assertCountEqual = self.assertItemsEqual
        except AttributeError:
            pass

    def test_division_listing(self):
        client = self.login()
        resp = client.get('/add/')
        matches = re.findall(r'<option.*?>(?P<name>[\w\s]+)</option>',
                resp.get_data(as_text=True))
        self.assertEqual(len(matches), 2)
        self.assertCountEqual(matches, ('Division 1', 'Division 3'))

    def test_submit_divisions(self):
        client = self.login()
        with self.app.test_request_context():
            user = User.query.filter_by(name=self.normal_name).one()
            divisions = views.requests.submit_divisions(user)
            division_names = [d[1] for d in divisions]
            self.assertEqual(len(division_names), 2)
            self.assertCountEqual(division_names, ('Division 1', 'Division 3'))

    def test_killmail_validation(self):
        # Using a test_client() context so the before_request callbacks are
        # called.
        with self.app.test_client() as c:
            c.get('/add/')
            # RequestsForm needs a list of divisions
            user = User.query.filter_by(name=self.normal_name).one()
            divisions = views.requests.submit_divisions(user)
            # Tests
            division = Division.query.filter_by(name='Division 1').one()
            zkb_form = views.requests.RequestForm(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True)
            zkb_form.division.choices = divisions
            # Fool InputRequired
            zkb_form.details.raw_data = zkb_form.details.data
            self.assertTrue(zkb_form.validate())
            crest_form = views.requests.RequestForm(
                    url=('http://public-crest.eveonline.com/killmails/'
                         '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'),
                    details='Foo',
                    division=division.id,
                    submit=True)
            crest_form.division.choices = divisions
            crest_form.details.raw_data = crest_form.details.data
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
            user = User.query.filter_by(name=self.normal_name).one()
            pilot = Pilot(user, 'Paxswill', 570140137)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        resp = client.post('/add/', follow_redirects=True, data=dict(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('38905408', resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(38905408)
            self.assertIsNotNone(request)

    def test_submit_non_personal_killmail(self):
        with self.app.test_request_context():
            user = User.query.filter_by(name=self.normal_name).one()
            pilot = Pilot(user, 'The Mittani', 443630591)
            db.session.add(pilot)
            db.session.commit()
            division = Division.query.filter_by(name='Division 1').one()
        client = self.login()
        resp = client.post('/add/', follow_redirects=True, data=dict(
                    url='https://zkillboard.com/kill/38905408/',
                    details='Foo',
                    division=division.id,
                    submit=True))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You can only submit killmails of characters you',
                resp.get_data(as_text=True))
        with self.app.test_request_context():
            request = Request.query.get(38905408)
            self.assertIsNone(request)

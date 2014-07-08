from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from ..util import TestApp, TestLogin
from evesrp import create_app, db
from evesrp.views import index, request_count
from evesrp.auth import PermissionType
from evesrp.auth.models import User, Division, Permission, Pilot
from evesrp.models import Request, ActionType


class TestIndexRedirect(TestApp):

    def test_anonymous_user(self):
        resp = self.app.test_client().get('/')
        self.assertTrue(resp.status_code, 302)
        self.assertIn('/login/', resp.headers['Location'])


class TestRequestCount(TestLogin):

    def setUp(self):
        super(TestRequestCount, self).setUp()
        with self.app.test_request_context():
            d1 = Division('Division 1')
            d2 = Division('Division 2')
            d3 = Division('Division 3')
            user = self.normal_user
            pilot = Pilot(user, 'A Pilot', 1)
            Permission(d1, PermissionType.submit, user)
            Permission(d2, PermissionType.review, user)
            Permission(d3, PermissionType.pay, user)
            db.session.commit()
            # Populate requests
            request_data = {
                'ship_type': 'Revenant',
                'corporation': 'Center of Applied Studies',
                'kill_timestamp': dt.datetime.utcnow(),
                'system': 'Jita',
                'constellation': 'Kimotoro',
                'region': 'The Forge',
                'pilot_id': 1,
            }
            for division in (d1, d2, d3):
                requests = (
                    # Division 1
                    Request(user, 'Foo', division, request_data.items(),
                        killmail_url='http://google.com',
                        status=ActionType.evaluating),
                    Request(user, 'Foo', division, request_data.items(),
                        killmail_url='http://google.com',
                        status=ActionType.incomplete),
                    Request(user, 'Foo', division, request_data.items(),
                        killmail_url='http://google.com',
                        status=ActionType.approved),
                    Request(user, 'Foo', division, request_data.items(),
                        killmail_url='http://google.com',
                        status=ActionType.paid),
                    Request(user, 'Foo', division, request_data.items(),
                        killmail_url='http://google.com',
                        status=ActionType.rejected),
                )
                db.session.add_all(requests)
            db.session.commit()

    def test_request_count(self):
        client = self.login()
        with client as c:
            # Get a request context by firing off a request
            c.get('/')
            for permission in (PermissionType.submit, PermissionType.review,
                    PermissionType.pay):
                self.assertEqual(request_count(permission), 1)
                for status in ActionType.statuses:
                    self.assertEqual(request_count(permission, status), 1)

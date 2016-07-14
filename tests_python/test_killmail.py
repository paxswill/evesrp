from __future__ import absolute_import
from unittest import TestCase
from decimal import Decimal
import re
import pytest
from httmock import HTTMock, all_requests, response
from evesrp import killmail


class TestKillmail(TestCase):

    def test_default_values(self):
        km = killmail.Killmail()
        attrs = (u'kill_id', u'ship_id', u'ship', u'pilot_id', u'pilot',
            u'corp_id', u'corp', u'alliance_id', u'alliance', u'verified',
            u'url', u'value', u'timestamp', u'system', u'constellation',
            u'region')
        for attr in attrs:
            self.assertIsNone(getattr(km, attr))

    def test_hidden_data(self):
        km = killmail.Killmail()
        old_dir = dir(km)
        km.foo = 'bar'
        new_dir = dir(km)
        self.assertEqual(old_dir, new_dir)
        self.assertIn(u'foo', km._data)
        self.assertEqual(km.foo, 'bar')

    def test_keyword_arguments(self):
        km = killmail.Killmail(kill_id=123456)
        self.assertEqual(km.kill_id, 123456)


class TestNameMixin(TestCase):

    def setUp(self):
        self.NameMixed = type('NameMixed', (killmail.Killmail,
                killmail.ShipNameMixin), dict())

    def test_devoter_id(self):
        km = self.NameMixed(ship_id=12017)
        self.assertEqual(km.ship, u'Devoter')


@pytest.fixture
def location_mixed():
    LocationMixed = type('LocationMixed', (killmail.Killmail,
                                           killmail.LocationMixin),
                         dict())
    return LocationMixed


class TestLocationMixin(object):

    def test_system(self, evesrp_app, crest, location_mixed):
        with evesrp_app.test_request_context():
            with HTTMock(crest):
                km = location_mixed(system_id=30000142)
                assert km.system == u'Jita'

    def test_constellation(self, evesrp_app, crest, location_mixed):
        with evesrp_app.test_request_context():
            with HTTMock(crest):
                km = location_mixed(system_id=30000142)
                assert km.constellation == u'Kimotoro'

    def test_region(self, evesrp_app, crest, location_mixed):
        with evesrp_app.test_request_context():
            with HTTMock(crest):
                km = location_mixed(system_id=30000142)
                assert km.region == u'The Forge'


class TestRequestsMixin(TestCase):

    def setUp(self):
        self.SessionMixed = type('SessionMixed', (killmail.Killmail,
                killmail.RequestsSessionMixin), dict())

    def test_default_creation(self):
        km = self.SessionMixed()
        self.assertIsNotNone(km.requests_session)

    def test_provided_session(self):
        session = object()
        km = self.SessionMixed(requests_session=session)
        self.assertIs(km.requests_session, session)


class TestZKillmail(object):

    def test_fw_killmail(self, zkillboard, crest):
        with HTTMock(zkillboard, crest):
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/37637533/')
            expected_values = {
                u'pilot': u'Paxswill',
                u'ship': u'Devoter',
                u'corp': u'Dreddit',
                u'alliance': u'Test Alliance Please Ignore',
                u'system': u'TA3T-3',
                u'domain': u'zkillboard.com',
                u'value': Decimal('273816945.63'),
            }
            for attr, value in expected_values.items():
                assert getattr(km, attr) == value

    def test_no_alliance_killmail(self, zkillboard, crest):
        with HTTMock(zkillboard, crest):
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/38862043/')
            expected_values = {
                u'pilot': u'Dave Duclas',
                u'ship': u'Breacher',
                u'corp': u'Omega LLC',
                u'alliance': None,
                u'system': u'Onatoh',
                u'domain': u'zkillboard.com',
                u'value': Decimal('10432408.70'),
            }
            for attr, value in expected_values.items():
                assert getattr(km, attr) == value

    def test_invalid_zkb_url(self):
        with pytest.raises(ValueError) as excinfo:
            killmail.ZKillmail('foobar')
        assert re.match(u"'.*' is not a valid zKillboard killmail",
                        str(excinfo.value))

    def test_invalid_zkb_response(self):
        @all_requests
        def bad_response(url, request):
            return response(status_code=403, content=u'')

        with HTTMock(bad_response):
            url = 'https://zkillboard.com/kill/38862043/'
            with pytest.raises(LookupError) as excinfo:
                killmail.ZKillmail(url)
            assert re.match(u"Error retrieving killmail data:.*",
                            str(excinfo.value))

    def test_invalid_kill_ids(self):
        @all_requests
        def empty_response(url, request):
            return response(content='[]')

        with HTTMock(empty_response):
            url = 'https://zkillboard.com/kill/0/'
            with pytest.raises(LookupError) as excinfo:
                killmail.ZKillmail(url)
            assert re.match(u"Invalid killmail: .*", str(excinfo.value))


class TestCRESTmail(object):

    def test_crest_killmails(self, crest):
        with HTTMock(crest):
            km = killmail.CRESTMail('http://crest-tq.eveonline.com/'
                    'killmails/30290604/'
                    '787fb3714062f1700560d4a83ce32c67640b1797/')
            expected_values = {
                u'pilot': u'CCP FoxFour',
                u'ship': u'Capsule',
                u'corp': u'C C P',
                u'alliance': u'C C P Alliance',
                u'system': u'Todifrauan',
            }
            for attr, value in expected_values.items():
                assert getattr(km, attr) == value

    def test_invalid_crest_url(self):
        with pytest.raises(ValueError) as excinfo:
            killmail.CRESTMail('foobar')
        assert re.match(u"'.*' is not a valid CREST killmail",
                        str(excinfo.value))

    def test_invalid_crest_response(self):
        @all_requests
        def bad_hash(url, request):
            return response(
                content=(u'{"message": "Invalid killmail ID or hash",'
                        u'"isLocalized": false, "key": "noSuchKill",'
                        u'"exceptionType": "ForbiddenError"}').encode('utf-8'),
                status_code=403)

        with HTTMock(bad_hash):
            url = ''.join(('http://crest-tq.eveonline.com/killmails/',
                    '30290604/787fb3714062f1700560d4a83ce32c67640b1797/'))
            with pytest.raises(LookupError) as excinfo:
                killmail.CRESTMail(url)
            assert re.match(u"Error retrieving CREST killmail:.*",
                            str(excinfo.value))

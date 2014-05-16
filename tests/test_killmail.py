from unittest import TestCase
try:
    from unittest.mock import patch, MagicMock
except ImportError:
    from mock import patch, MagicMock

from evesrp import killmail


class TestKillmail(TestCase):

    def test_default_values(self):
        km = killmail.Killmail()
        attrs = ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
            'corp_id', 'corp', 'alliance_id', 'alliance', 'verified',
            'url', 'value', 'timestamp', 'system', 'constellation',
            'region')
        for attr in attrs:
            self.assertTrue(getattr(km, attr) is None)

    def test_hidden_data(self):
        km = killmail.Killmail()
        old_dir = dir(km)
        km.foo = 'bar'
        new_dir = dir(km)
        self.assertEqual(old_dir, new_dir)
        self.assertTrue('foo' in km._data)
        self.assertEqual(km.foo, 'bar')

    def test_keyword_arguments(self):
        km = killmail.Killmail(kill_id=123456)


class TestNameMixin(TestCase):

    def setUp(self):
        self.NameMixed = type('NameMixed', (killmail.Killmail,
                killmail.ShipNameMixin), dict())

    def test_devoter_id(self):
        km = self.NameMixed(ship_id=12017)
        self.assertEqual(km.ship, 'Devoter')


class TestLocationMixin(TestCase):

    def setUp(self):
        self.LocationMixed = type('LocationMixed', (killmail.Killmail,
                killmail.LocationMixin), dict())

    def test_system(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.system, 'Jita')

    def test_constellation(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.constellation, 'Kimotoro')

    def test_region(self):
        km = self.LocationMixed(system_id=30000142)
        self.assertEqual(km.region, 'The Forge')


class TestRequestsMixin(TestCase):

    def setUp(self):
        self.SessionMixed = type('SessionMixed', (killmail.Killmail,
                killmail.RequestsSessionMixin), dict())

    def test_default_creation(self):
        km = self.SessionMixed()
        self.assertTrue(km.requests_session is not None)

    def test_provided_session(self):
        session = object()
        km = self.SessionMixed(requests_session=session)
        self.assertTrue(km.requests_session is session)


class TestZKillmail(TestCase):

    paxswill_resp = [{
        'killID': '37637533',
        'solarSystemID': '30001228',
        'killTime': '2014-03-20 02:32:00',
        'moonID': '0',
        'victim': {
            'shipTypeID': '12017',
            'damageTaken': '25198',
            'factionName': 'Caldari State',
            'factionID': '500001',
            'allianceName': 'Test Alliance Please Ignore',
            'allianceID': '498125261',
            'corporationName': 'Dreddit',
            'corporationID': '1018389948',
            'characterName': 'Paxswill',
            'characterID': '570140137',
            'victim': '',
        },
        'zkb': {
            'totalValue': '273816945.63',
            'points': '22',
            'involved': 42,
        }
    }]

    no_alliance_resp = [{
        'killID': '38862043',
        'solarSystemID': '30002811',
        'killTime': '2014-05-15 03:11:00',
        'moonID': '0',
        'victim': {
            'shipTypeID': '598',
            'damageTaken': '1507',
            'factionName': '',
            'factionID': '0',
            'allianceName': '',
            'allianceID': '0',
            'corporationName': 'Omega LLC',
            'corporationID': '98070272',
            'characterName': 'Dave Duclas',
            'characterID': '90741463',
            'victim': '',
        },
        'zkb': {
            'totalValue': '10432408.70',
            'points': '8',
            'involved': 1,
        }
    }]

    @staticmethod
    def _configure_mock_session(mock_session, resp):
        mock_response = MagicMock()
        mock_response.json.return_value = resp
        session_instance = mock_session.return_value
        session_instance.get.return_value = mock_response
        return session_instance

    def test_fw_killmail(self):
        with patch('requests.Session') as mock_session:
            session = self._configure_mock_session(mock_session,
                    self.paxswill_resp)
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/37637533/')
            session.get.assert_called_with(
                    'https://zkillboard.com/api/killID/37637533')
            expected_values = {
                'pilot': 'Paxswill',
                'ship': 'Devoter',
                'corp': 'Dreddit',
                'alliance': 'Test Alliance Please Ignore',
                'system': 'TA3T-3',
                'domain': 'zkillboard.com'
            }
            for attr, value in expected_values.items():
                self.assertEqual(getattr(km, attr), value,
                        msg='{} is not {}'.format(attr, value))

    def test_no_alliance_killmail(self):
        with patch('requests.Session') as mock_session:
            session = self._configure_mock_session(mock_session,
                    self.no_alliance_resp)
            # Actual testing
            km = killmail.ZKillmail('https://zkillboard.com/kill/38862043/')
            session.get.assert_called_with(
                    'https://zkillboard.com/api/killID/38862043')
            expected_values = {
                'pilot': 'Dave Duclas',
                'ship': 'Breacher',
                'corp': 'Omega LLC',
                'alliance': None,
                'system': 'Onatoh',
                'domain': 'zkillboard.com'
            }
            for attr, value in expected_values.items():
                self.assertEqual(getattr(km, attr), value,
                        msg='{} is not {}'.format(attr, value))


class TestCRESTmail(TestCase):
    pass




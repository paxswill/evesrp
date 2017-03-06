import types
try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp import storage, static_data


# Creating the Bravado client involves getting the swagger spec and parsing it.
# It takes a while, and is 100% sharable between test runs (there is no shared
# state).
@pytest.fixture(scope='session')
def ccp_store():
    # NOTE: This is a live test, against CCP's live ESI servers. This means it
    # /may/ experience downtime as their service does. It also will expose any
    # problems due to updating APIs.
    store = storage.CcpStore()
    # Instrument/replace _esi_request to check for warning headers
    original_esi_request = store._esi_request
    def warning_esi_request(*args, **kwargs):
        result = original_esi_request(*args, **kwargs)
        assert u'warning' not in result
        return result
    store._esi_request = warning_esi_request
    return store


@pytest.fixture(scope='session')
def _caching_store():
    store = storage.CachingCcpStore()
    # Get a list of the names of all public members of an instance (the storage
    # instance in this case).
    public_attrs = [attr for attr in dir(store) if not attr.startswith('_')]
    # Filter out things that aren't methods
    methods = [attr for attr in public_attrs if
               isinstance(getattr(store, attr), types.MethodType)]
    # Now wrap every method in a mock instance set up to pas things through so
    # we can watch which calls are made
    for method_name in methods:
        method = getattr(store, method_name)
        mock_method = mock.Mock()
        mock_method.side_effect = method
        setattr(store, method_name, mock_method)
        setattr(store, "_original_{}".format(method_name), method)
    store._mocked_methods = methods
    return store


@pytest.fixture(params=(True, False), ids=('cache_hit', 'cache_not_hit'))
def hit_cache(request):
    return request.param


@pytest.fixture(scope='function')
def caching_store(_caching_store):
    # reset call counts between test function calls
    for method_name in _caching_store._mocked_methods:
        mocked_method = getattr(_caching_store, method_name)
        mocked_method.reset_mock()
    return _caching_store


class TestSimpleCcpStore(object):

    def test_region_id(self, ccp_store):
        assert ccp_store.get_region_id('The Forge')[u'result'] == 10000002

    def test_region_name(self, ccp_store):
        assert ccp_store.get_region_name(10000002)[u'result'] == 'The Forge'

    def test_constellation_id(self, ccp_store):
        assert ccp_store.get_constellation_id('Kimotoro')[u'result'] == 20000020

    def test_constellation_name(self, ccp_store):
        assert ccp_store.get_constellation_name(20000020)[u'result'] == \
            'Kimotoro'

    def test_system_id(self, ccp_store):
        assert ccp_store.get_system_id('Jita')[u'result'] == 30000142

    def test_system_name(self, ccp_store):
        assert ccp_store.get_system_name(30000142)[u'result'] == 'Jita'

    @pytest.mark.parametrize('name,id_', (
        # Normal 2010 vintage character
        ('Paxswill', 570140137),
        # 2014 vintage character, but using a name that was claimed after being
        # released by CCP from a trial account that never subscribed. For a
        # time, both this character and the old character were returned in-game
        # when searching for 'Iusia'
        ('Iusia', 95189399),
        # 2017 vintage character, in the new ID number range
        ('Cpt Hector', 2112390815),
    ))
    def test_character_id(self, ccp_store, name, id_):
        assert ccp_store.get_character_id(name)[u'result'] == id_

    @pytest.mark.parametrize('name,id_', (
        # Normal 2010 vintage character
        ('Paxswill', 570140137),
        # Not testing reassigned names, as it doesn't matter for this direction
        # of mapping.
        # 2017 vintage character, in the new ID number range
        ('Cpt Hector', 2112390815),
    ))
    def test_character_name(self, ccp_store, name, id_):
        assert ccp_store.get_character_name(id_)[u'result'] == name

    @pytest.mark.parametrize('get_args,id_', (
        # Player corporation
        ({'corporation_name': 'Dreddit'}, 1018389948),
        ({'character_name': 'Paxswill'}, 1018389948),
        ({'character_id': 570140137}, 1018389948),
        # NPC corp
        ({'corporation_name': 'State War Academy'}, 1000167),
        # TODO: Add test case for closed corporations
        # Need to find a closed corporation to test agains. Maybe make one
        # myself just for testing...).
    ))
    def test_corporation_id(self, ccp_store, get_args, id_):
        assert ccp_store.get_corporation_id(**get_args)[u'result'] == id_

    @pytest.mark.parametrize('name,id_', (
        # Player corporation
        ('Dreddit', 1018389948),
        # NPC corp
        ('State War Academy', 1000167),
    ))
    def test_corporation_name(self, ccp_store, name, id_):
        assert ccp_store.get_corporation_name(id_)[u'result'] == name

    @pytest.mark.parametrize('get_args,id_',(
        ({'alliance_name': 'Test Alliance Please Ignore'}, 498125261),
        ({'corporation_name': 'C C P'}, 434243723),
        ({'corporation_id': 109299958}, 434243723),
    ))
    def test_alliance_id(self, get_args, id_, ccp_store):

        assert ccp_store.get_alliance_id(**get_args)[u'result'] == id_

    def test_alliance_name(self, ccp_store):
        assert ccp_store.get_alliance_name(498125261)[u'result'] == \
            'Test Alliance Please Ignore'

    def get_type_id(self, ccp_store):
        # Test the Cruor specifically, as there are two types for the single
        # name
        assert ccp_store.get_type_id('Cruor')[u'result'] == 17926

    def get_type_name(self, ccp_store):
        assert ccp_store.get_type_name(17926)[u'result'] == 'Cruor'


class TestCachedCcpStore(object):

    def test_region_id(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.region_names, 10000002)
            assert 10000002 not in static_data.region_names
        assert caching_store.get_region_id('The Forge')[u'result'] == 10000002

    def test_region_name(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.region_names, 10000002)
            assert 10000002 not in static_data.region_names
        assert caching_store.get_region_name(10000002)[u'result'] == 'The Forge'

    def test_constellation_id(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.constellation_names, 20000020)
            assert 20000020 not in static_data.constellation_names
        assert caching_store.get_constellation_id('Kimotoro')[u'result'] == \
            20000020

    def test_constellation_name(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.constellation_names, 20000020)
            assert 20000020 not in static_data.constellation_names
        assert caching_store.get_constellation_name(20000020)[u'result'] == \
            'Kimotoro'

    def test_system_id(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.system_names, 30000142)
            assert 30000142 not in static_data.system_names
        assert caching_store.get_system_id('Jita')[u'result'] == 30000142

    def test_system_name(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.system_names, 30000142)
            assert 30000142 not in static_data.system_names
        assert caching_store.get_system_name(30000142)[u'result'] == 'Jita'

    def test_type_id(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.ships, 11567)
            assert 11567 not in static_data.ships
        assert caching_store.get_type_id('Avatar')[u'result'] == 11567

    def test_type_name(self, caching_store, hit_cache, monkeypatch):
        if not hit_cache:
            monkeypatch.delitem(static_data.ships, 11567)
            assert 11567 not in static_data.ships
        assert caching_store.get_type_name(11567)[u'result'] == 'Avatar'

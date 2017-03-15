import pytest
import requests
import six

from evesrp import storage, static_data


if six.PY3:
    unicode = str


@pytest.fixture(scope='session')
def requests_session():
    session = requests.Session()
    user_agent = 'EVE-SRP-Testing/0.1 (paxswill@paxswill.com)'
    session.headers.update({'User-Agent': user_agent})
    return session


# Creating the Bravado client involves getting the swagger spec and parsing it.
# It takes a while, and is 100% sharable between test runs (there is no shared
# state).
@pytest.fixture(scope='session')
def ccp_store(requests_session):
    # NOTE: This is a live test, against CCP's live ESI servers. This means it
    # /may/ experience downtime as their service does. It also will expose any
    # problems due to updating APIs.
    store = storage.CcpStore(requests_session=requests_session)
    # Instrument/replace _esi_request to check for warning headers
    original_esi_request = store._esi_request

    def warning_esi_request(*args, **kwargs):
        result = original_esi_request(*args, **kwargs)
        assert u'warning' not in result
        return result
    store._esi_request = warning_esi_request
    return store


@pytest.fixture(scope='session')
def _caching_store(requests_session):
    store = storage.CachingCcpStore(requests_session=requests_session)
    """
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
    """
    return store


@pytest.fixture(params=(True, False), ids=('cache_hit', 'cache_not_hit'))
def hit_cache(request):
    return request.param


@pytest.fixture(scope='function')
def caching_store(_caching_store):
    # reset call counts between test function calls
    """
    for method_name in _caching_store._mocked_methods:
        mocked_method = getattr(_caching_store, method_name)
        mocked_method.reset_mock()
        """
    return _caching_store


def _kwarg_id(kwarg):
    if len(kwarg) == 0:
        return "empty"
    key, value = kwarg.popitem()
    kwarg[key] = value
    return "{}_{}".format(key, value)


@pytest.fixture(params=('region', 'constellation', 'system'))
def location_type(request):
    return request.param


@pytest.fixture
def location(location_type):
    if location_type == 'region':
        return {
            u'name': u'The Forge',
            u'id': 10000002,
        }
    elif location_type == 'constellation':
        return {
            u'name': u'Kimotoro',
            u'id': 20000020,
        }
    elif location_type == 'system':
        return {
            u'name': u'Jita',
            u'id': 30000142,
        }


@pytest.fixture(params=(
    {'region_name': u'The Forge'},
    {'region_id': 10000002},
    {'constellation_name': u'Kimotoro'},
    {'constellation_id': 20000020},
    {'system_name': u'Jita'},
    {'system_id': 30000142},
    {},
), ids=_kwarg_id)
def location_kwargs(request):
    return request.param


class TestSimpleCcpStore(object):

    def test_location(self, ccp_store, location, location_type,
                      location_kwargs):
        try:
            key = list(location_kwargs.keys())[0]
            # Skip early
            if location_type == 'constellation' and 'region' in key:
                pytest.skip("region_* kwargs not valid for get_constellation")
            elif location_type == 'system' and ('region' in key or
                                                'constellation' in key):
                pytest.skip("region_* and constellation_* kwargs not valid for"
                            " get_system")
        except IndexError:
            # Don't skip the empty kwargs case
            pass
        get_location = getattr(ccp_store, 'get_' + location_type)
        if len(location_kwargs) == 0:
            with pytest.raises(ValueError):
                get_location(**location_kwargs)
        else:
            result = get_location(**location_kwargs)[u'result']
            assert location == result

    @pytest.mark.parametrize('location_negative_kwargs', (
        {'region_name': 'Not a Region Name'},
        {'region_id': 0},
        {'constellation_name': 'Not a Constellation Name'},
        {'constellation_id': 0},
        {'system_name': 'Not a System Name'},
        {'system_id': 0},
    ), ids=_kwarg_id)
    def test_location_negative(self, ccp_store, location_type,
                               location_negative_kwargs):
        key = list(location_negative_kwargs.keys())[0]
        # Skip early
        if location_type == 'constellation' and 'region' in key:
            pytest.skip("region_* kwargs not valid for get_constellation")
        elif location_type == 'system' and ('region' in key or
                                            'constellation' in key):
            pytest.skip("region_* and constellation_* kwargs not valid for "
                        "get_system")
        get_location = getattr(ccp_store, 'get_' + location_type)
        resp = get_location(**location_negative_kwargs)
        assert resp[u'result'] is None
        assert unicode(location_negative_kwargs[key]) in resp[u'errors'][0]

    @pytest.fixture(params=('alliance', 'corporation', 'character'))
    def identity_type(self, request):
        return request.param

    @pytest.fixture(params=(
        {'character_id': 570140137},
        {'character_id': 95189399},
        {'character_id': 2112390815},
        {'corporation_id': 1018389948},
        {'corporation_id': 1000167},
        {'corporation_id': 1000166},
        {'corporation_id': 109299958},
        {'alliance_id': 434243723},
        {'alliance_id': 498125261},
        {'character_name': u'Paxswill'},
        {'character_name': u'Iusia'},
        {'character_name': u'Cpt Hector'},
        {'corporation_name': u'Dreddit'},
        {'corporation_name': u'State War Academy'},
        {'corporation_name': u'Imperial Academy'},
        {'corporation_name': u'C C P'},
        {'alliance_name': u'Test Alliance Please Ignore'},
        {'alliance_name': u'C C P Alliance'},
    ), ids=_kwarg_id)
    def identity_kwargs(self, request):
        return request.param

    @pytest.fixture
    def expected_identity(self, identity_type, identity_kwargs):
        # Peek at the value
        key, value = identity_kwargs.popitem()
        identity_kwargs[key] = value
        test_alliance = {
            u'id': 498125261,
            u'name': u'Test Alliance Please Ignore',
        }
        b0rt = {
            u'id': 1018389948,
            u'name': u'Dreddit',
        }
        swa = {
            u'id': 1000167,
            u'name': u'State War Academy',
        }
        iac = {
            u'id': 1000166,
            u'name': u'Imperial Academy',
        }
        ccp_alliance = {
            u'id': 434243723,
            u'name': u'C C P Alliance',
        }
        ccp_corp = {
            u'id': 109299958,
            u'name': u'C C P',
        }
        identities = {
            # Characters
            570140137: {
                'alliance': test_alliance,
                'corporation': b0rt,
                'character': {
                    u'id': 570140137,
                    u'name': u'Paxswill',
                },
            },
            95189399: {
                'alliance': None,
                'corporation': swa,
                'character': {
                    u'id': 95189399,
                    u'name': u'Iusia',
                },
            },
            2112390815: {
                'alliance': None,
                'corporation': iac,
                'character': {
                    u'id': 2112390815,
                    u'name': 'Cpt Hector',
                },
            },
            # Corps
            b0rt[u'id']: {
                'corporation': b0rt,
                'alliance': test_alliance,
            },
            swa[u'id']: {
                'corporation': swa,
                'alliance': None,
            },
            iac[u'id']: {
                'corporation': iac,
                'alliance': None,
            },
            ccp_corp[u'id']: {
                'corporation': ccp_corp,
                'alliance': ccp_alliance,
            },
            # Alliances
            test_alliance[u'id']: {
                'alliance': test_alliance,
            },
            ccp_alliance[u'id']: {
                'alliance': ccp_alliance,
            },
        }
        # Skip invalid tests
        if (identity_type == 'corporation' and 'alliance' in key) or \
                (identity_type == 'character' and
                 ('alliance' in key or 'corporation' in key)):
            pytest.skip("keyword argument {} not supported for "
                        "get_{}".format(key, identity_type))
        # Actual work
        if key.endswith('_id'):
            return identities[value][identity_type]
        elif key.endswith('_name'):
            kwarg_type = key[:-5]
            # Find the identity for this argument
            for identity_key, identity_dict in six.iteritems(identities):
                try:
                    identity = identity_dict[kwarg_type]
                    if identity is not None and identity[u'name'] == value:
                        return identity_dict[identity_type]
                except KeyError:
                    pass
        raise Exception("Something's wrong in expected_identity, you should "
                        "never reach here.")

    def test_identity(self, ccp_store, identity_kwargs, identity_type,
                      expected_identity):
        if identity_type == 'character':
            get_identity = ccp_store.get_ccp_character
        else:
            get_identity = getattr(ccp_store, 'get_' + identity_type)
        result = get_identity(**identity_kwargs)
        assert result[u'result'] == expected_identity

    @pytest.mark.parametrize('negative_kwargs', (
        {'alliance_id': 0},
        {'corporation_id': 0},
        {'character_id': 0},
        # Using the non-spaced names, as the real names are spaced out and a
        # player trying to claim these names would et hit for impersonation.
        {'alliance_name': 'CCP Alliance'},
        {'corporation_name': 'CCP Corporation'},
        # Use a CCP name that's probably never happening
        {'character_name': 'CCP Paxswill'},
    ), ids=_kwarg_id)
    def test_identity_negative(self, ccp_store, negative_kwargs,
                               identity_type):
        # Skip invalid combos
        key = list(negative_kwargs.keys())[0]
        if (identity_type == 'corporation' and 'alliance' in key) or \
                (identity_type == 'character' and
                 ('alliance' in key or 'corporation' in key)):
            pytest.skip("keyword argument {} not supported for "
                        "get_{}".format(key, identity_type))
        # Actual test
        if identity_type == 'character':
            get_identity = ccp_store.get_ccp_character
        else:
            get_identity = getattr(ccp_store, 'get_' + identity_type)
        resp = get_identity(**negative_kwargs)
        assert resp[u'result'] is None
        assert unicode(negative_kwargs[key]) in resp[u'errors'][0]

    @pytest.mark.parametrize('get_kwargs,expected', (
        ({'type_id': 17926}, {u'id': 17926, u'name': u'Cruor'}),
        ({'type_name': u'Cruor'}, {u'id': 17926, u'name': u'Cruor'}),
        ({}, None),
        ({'type_name': u'Not a Real Type'}, None),
        ({'type_name': u'Avatar'}, {u'id': 11567, u'name': u'Avatar'}),
        ({'type_id': 11567}, {u'id': 11567, u'name': u'Avatar'}),
    ))
    def test_get_type(self, ccp_store, get_kwargs, expected):
        if len(get_kwargs) == 0:
            # negative test for no kwargs error
            with pytest.raises(ValueError):
                ccp_store.get_type(**get_kwargs)
        else:
            resp = ccp_store.get_type(**get_kwargs)
            assert resp[u'result'] == expected
            if expected is None:
                assert 'Not Found' in resp[u'errors'][0]


class TestCachedCcpStore(object):

    def test_location(self, caching_store, location, location_type,
                      location_kwargs, hit_cache, monkeypatch):
        try:
            key = list(location_kwargs.keys())[0]
            # Skip early
            if location_type == 'constellation' and 'region' in key:
                pytest.skip("region_* kwargs not valid for get_constellation")
            elif location_type == 'system' and ('region' in key or
                                                'constellation' in key):
                pytest.skip("region_* and constellation_* kwargs not valid for"
                            " get_system")
            if not hit_cache:
                if location_type == 'region' and key.startswith(
                        'constellation'):
                    monkeypatch.delitem(static_data.constellations_to_regions,
                                        20000020)
                elif location_type in ('region', 'constellation') and \
                        key.startswith('system'):
                    monkeypatch.delitem(static_data.systems_to_constellations,
                                        30000142)
                elif key.startswith(key):
                    static_map = getattr(static_data, location_type + '_names')
                    monkeypatch.delitem(static_map, location[u'id'])
                else:
                    raise Exception("Test error, cache miss logic error.")
        except IndexError:
            # Don't skip the empty kwargs case
            pass
        get_location = getattr(caching_store, 'get_' + location_type)
        # Expect an exception when passing no kwargs
        if len(location_kwargs) == 0:
            with pytest.raises(ValueError):
                get_location(**location_kwargs)
        else:
            result = get_location(**location_kwargs)[u'result']
            assert location == result

    @pytest.mark.parametrize('get_kwargs,expected', (
        ({'type_id': 17926}, {u'id': 17926, u'name': u'Cruor'}),
        ({'type_name': u'Cruor'}, {u'id': 17926, u'name': u'Cruor'}),
        ({}, None),
        ({'type_name': u'Not a Real Type'}, None),
        ({'type_name': u'Avatar'}, {u'id': 11567, u'name': u'Avatar'}),
        ({'type_id': 11567}, {u'id': 11567, u'name': u'Avatar'}),
    ))
    def test_get_types(self, get_kwargs, expected, caching_store, hit_cache,
                       monkeypatch):
        if not hit_cache:
            # Just remove both the Avatar and Cruor
            monkeypatch.delitem(static_data.ships, 11567)
            monkeypatch.delitem(static_data.ships, 17926)
        if len(get_kwargs) == 0:
            # negative test for no kwargs error
            with pytest.raises(ValueError):
                caching_store.get_type(**get_kwargs)
        else:
            resp = caching_store.get_type(**get_kwargs)
            assert resp[u'result'] == expected
            if expected is None:
                assert 'Not Found' in resp[u'errors'][0]

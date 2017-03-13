import pytest


@pytest.fixture
def store():
    raise NotImplementedError


@pytest.fixture
def populated_store(store):
    # Again, subclass TestStorage and override store and populated_store
    raise NotImplementedError


@pytest.fixture(params=('user', 'group'))
def authn_entity_name(request):
    return request.param

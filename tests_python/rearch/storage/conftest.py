import uuid

import pytest

from evesrp import new_models as models


@pytest.fixture
def store():
    raise NotImplementedError


@pytest.fixture
def populated_store(store):
    # Again, subclass TestStorage and override store and populated_store
    raise NotImplementedError


@pytest.fixture(params=('user', 'group'))
def entity_type(request):
    return request.param


@pytest.fixture
def auth_provider_uuid():
    return uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521')


@pytest.fixture
def auth_provider_key(entity_type):
    if entity_type == 'user':
        return 'authn_user'
    elif entity_type == 'group':
        return 'authn_group'


@pytest.fixture
def authn_entity_dict(entity_type, auth_provider_uuid, auth_provider_key):
    if entity_type == 'user':
        return {
            'user_id': 987,
            'provider_uuid': auth_provider_uuid,
            'provider_key': auth_provider_key,
            'extra_data': {},
        }
    elif entity_type == 'group':
        return {
            'group_id': 876,
            'provider_uuid': auth_provider_uuid,
            'provider_key': auth_provider_key,
            'extra_data': {},
        }


@pytest.fixture
def authn_entity(authn_entity_dict):
    if 'user_id' in authn_entity_dict:
        return models.AuthenticatedUser.from_dict(authn_entity_dict)
    elif 'group_id' in authn_entity_dict:
        return models.AuthenticatedGroup.from_dict(authn_entity_dict)

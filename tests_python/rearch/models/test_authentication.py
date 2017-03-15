try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp.new_models import authentication as authn


@pytest.fixture(params=(True, False),
                ids=('use_entity_object', 'use_entity_id'))
def use_entity_obj(request):
    return request.param


@pytest.fixture(params=(True, False),
                ids=('use_provider_object', 'use_provider_id'))
def use_provider_obj(request):
    return request.param


@pytest.fixture(params=('user', 'group'))
def auth_entity(request):
    return request.param


@pytest.mark.parametrize('extra_kwargs', (True, False),
                         ids=('add_extra_kwargs', 'no_kwargs'))
def test_auth_entity_init(auth_entity, use_entity_obj, use_provider_obj,
                          extra_kwargs):
    kwargs = {
        'provider_key': mock.sentinel.provider_key,
        'extra_data': {'test_extra': mock.sentinel.test_extra},
    }
    if use_provider_obj:
        kwargs['provider'] = mock.Mock(uuid=mock.sentinel.provider_uuid)
    else:
        kwargs['provider_uuid'] = mock.sentinel.provider_uuid
    if auth_entity == 'user':
        AuthenticatedEntity = authn.AuthenticatedUser
    elif auth_entity == 'group':
        AuthenticatedEntity = authn.AuthenticatedGroup
    if use_entity_obj:
        kwargs[auth_entity] = mock.Mock(id_=mock.sentinel.entity_id)
    else:
        kwargs[auth_entity + '_id'] = mock.sentinel.entity_id
    if extra_kwargs:
        kwargs['test_extra_two'] = mock.sentinel.test_extra_two
    entity = AuthenticatedEntity(**kwargs)
    assert entity.provider_key == mock.sentinel.provider_key
    assert entity.provider_uuid == mock.sentinel.provider_uuid
    assert getattr(entity, auth_entity + '_id') == mock.sentinel.entity_id
    if extra_kwargs:
        assert entity.extra_data == {
            'test_extra': mock.sentinel.test_extra,
            'test_extra_two': mock.sentinel.test_extra_two,
        }
    else:
        assert entity.extra_data == {
            'test_extra': mock.sentinel.test_extra,
        }


def test_auth_user_from_dict(auth_entity):
    auth_entity_data = {
        (auth_entity + '_id'): mock.sentinel.entity_id,
        'provider_key': mock.sentinel.provider_key,
        'provider_uuid': mock.sentinel.provider_uuid,
        'extra_data': {'test_extra': mock.sentinel.test_extra},
    }
    if auth_entity == 'user':
        AuthenticatedEntity = authn.AuthenticatedUser
    elif auth_entity == 'group':
        AuthenticatedEntity = authn.AuthenticatedGroup
    entity = AuthenticatedEntity.from_dict(auth_entity_data)
    assert entity.provider_key == mock.sentinel.provider_key
    assert entity.provider_uuid == mock.sentinel.provider_uuid
    assert entity.extra_data == {'test_extra': mock.sentinel.test_extra}
    assert getattr(entity, auth_entity + '_id') == mock.sentinel.entity_id


def test_set_extra_data():
    auth_user = authn.AuthenticatedUser(user_id=0, provider_uuid=None,
                                        provider_key=None)
    assert auth_user.extra_data == {}
    auth_user.testing_extra_data = mock.sentinel.test_extra
    expected_extra = {
        'testing_extra_data': mock.sentinel.test_extra
    }
    assert auth_user.extra_data == expected_extra


def test_get_extra_data():
    auth_user = authn.AuthenticatedUser(user_id=0, provider_uuid=None,
                                        provider_key=None,
                                        extra_data={'testing':
                                                    mock.sentinel.get_extra})
    assert auth_user.extra_data == {
        'testing': mock.sentinel.get_extra,
    }
    assert auth_user.testing == mock.sentinel.get_extra
    with pytest.raises(AttributeError):
        auth_user.missing_test


def test_delete_extra_data():
    auth_user = authn.AuthenticatedUser(user_id=0, provider_uuid=None,
                                        provider_key=None,
                                        extra_data={'testing':
                                                    mock.sentinel.get_extra})
    assert auth_user.extra_data == {
        'testing': mock.sentinel.get_extra,
    }
    del auth_user.testing
    assert auth_user.extra_data == {}
    with pytest.raises(AttributeError):
        del auth_user.testing

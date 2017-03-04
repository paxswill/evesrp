try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp.new_models import authentication as authn


@pytest.fixture(params=(True, False), ids=('use_user_object', 'use_user_id'))
def use_user_obj(request):
    return request.param


@pytest.fixture(params=(True, False),
                ids=('use_provider_object', 'use_provider_id'))
def use_provider_obj(request):
    return request.param


def test_auth_user_init(use_user_obj, use_provider_obj):
    kwargs = {
        'provider_key': mock.sentinel.provider_key,
        'extra_data': mock.sentinel.extra_data,
    }
    if use_provider_obj:
        kwargs['provider'] = mock.Mock(uuid=mock.sentinel.provider_uuid)
    else:
        kwargs['provider_uuid'] = mock.sentinel.provider_uuid
    if use_user_obj:
        kwargs['user'] = mock.Mock(id_=mock.sentinel.user_id)
    else:
        kwargs['user_id'] = mock.sentinel.user_id
    auth_user = authn.AuthenticatedUser(**kwargs)
    assert auth_user.provider_key == mock.sentinel.provider_key
    assert auth_user.user_id == mock.sentinel.user_id
    assert auth_user.provider_uuid == mock.sentinel.provider_uuid
    assert auth_user.extra_data == mock.sentinel.extra_data


@pytest.mark.parametrize('with_extra', (True, False),
                         ids=('with_extra', 'no_extra'))
def test_auth_user_from_dict(with_extra):
    auth_user_data = {
        'user_id': mock.sentinel.user_id,
        'provider_key': mock.sentinel.provider_key,
        'provider_uuid': mock.sentinel.provider_uuid,
        'extra_data': {},
    }
    if with_extra:
        auth_user_data['extra_data'] = mock.sentinel.extra_data
    auth_user = authn.AuthenticatedUser.from_dict(auth_user_data)
    assert auth_user.provider_key == mock.sentinel.provider_key
    assert auth_user.user_id == mock.sentinel.user_id
    assert auth_user.provider_uuid == mock.sentinel.provider_uuid
    if with_extra:
        assert auth_user.extra_data == mock.sentinel.extra_data
    else:
        assert auth_user.extra_data == {}


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

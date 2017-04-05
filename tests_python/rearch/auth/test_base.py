try:
    from unittest import mock
except ImportError:
    import mock
import uuid
from evesrp.new_auth import base as auth_base


def test_base_init():
    provider = auth_base.AuthenticationProvider(mock.sentinel.store)
    assert provider.store == mock.sentinel.store


def test_base_uuid():
    provider = auth_base.AuthenticationProvider(None)
    assert provider.uuid == uuid.UUID('1949aa92-581f-5c26-ac54-6dfa5e43a7c7')

    class ProviderSub(auth_base.AuthenticationProvider):
        pass
    assert ProviderSub(None).uuid == \
        uuid.UUID('6751e9d0-2e95-5d26-aaf5-7ea7bcdd5f52')


def test_base_name():
    provider1 = auth_base.AuthenticationProvider(None, name=None)
    assert provider1.name == u'Base Authentication'
    provider2 = auth_base.AuthenticationProvider(None, name=mock.sentinel.name)
    assert provider2.name == mock.sentinel.name


def test_base_admins():
    provider1 = auth_base.AuthenticationProvider(None,
                                                 admins=[mock.sentinel.admins])
    assert provider1.admins == [mock.sentinel.admins]
    provider2 = auth_base.AuthenticationProvider(None)
    assert provider2.admins == []


def test_base_fields():
    provider = auth_base.AuthenticationProvider(None)
    assert len(provider.fields) == 1
    assert next(iter(provider.fields.items())) == (u'submit', u'Log In')

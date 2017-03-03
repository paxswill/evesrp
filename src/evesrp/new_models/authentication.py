import json

from . import util


class AuthenticatedUser(util.IdEquality):

    # If I ever end up dropping support for Py2, these arguments will become
    # by keyword only
    def __init__(self, provider_key, extra_data=None, **kwargs):
        self.user_id = util.id_from_kwargs('user', kwargs)
        if 'provider' not in kwargs and \
                'provider_guid' not in kwargs:
            raise ValueError(u"Neither 'provider' nor 'provider_guid' have "
                             u"been supplied.")
        elif 'provider' in kwargs:
            self.provider_guid = kwargs['provider'].guid
        else:
            self.provider_guid = kwargs['provider_guid']
        if extra_data is None:
            extra_data = {}
        self.extra_data = extra_data
        self.provider_key = provider_key

    @classmethod
    def from_dict(cls, user_dict):
        return cls(user_id=user_dict['user_id'],
                   provider_guid=user_dict['provider_guid'],
                   provider_key=user_dict['provider_key'],
                   extra_data=user_dict['extra_data'])

    def __getattr__(self, name):
        try:
            return self.extra_data[name]
        except KeyError:
            raise AttributeError

    def __setattr__(self, name, value):
        if name in {'user_id', 'provider_guid', 'provider_key', 'extra_data'}:
            super(AuthenticatedUser, self).__setattr__(name, value)
        else:
            if self.extra_data is None:
                self.extra_data = {}
            self.extra_data[name] = value

    def __delattr__(self, name):
        try:
            del self.extra_data[name]
        except KeyError:
            raise AttributeError

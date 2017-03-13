from . import util


class _AbstractAuthenticated(object):

    # If I ever end up dropping support for Py2, these arguments will become
    # by keyword only
    def __init__(self, provider_key, extra_data=None, **kwargs):
        if 'provider' not in kwargs and \
                'provider_uuid' not in kwargs:
            raise ValueError(u"Neither 'provider' nor 'provider_uuid' have "
                             u"been supplied.")
        elif 'provider' in kwargs:
            self.provider_uuid = kwargs.pop('provider').uuid
        else:
            self.provider_uuid = kwargs.pop('provider_uuid')
        self.provider_key = provider_key
        """
        Things to cram inside extra_data:

            * OAuth refresh keys and expiration times
            * Whether a group is a special admin 'virtual' group (one created
              so you can refer to just the admins of a group as defined by some
              authentication backends like TEST Auth).
            * EveSSO's AccountCharacterHash

        Basically, if it's only relevant to a AuthenticationProvider, then it
        goes in extra_data.
        """
        if extra_data is None:
            extra_data = {}
        self.extra_data = extra_data
        for attr in self._normal_attrs:
            kwargs.pop(attr, None)
        self.extra_data.update(kwargs)


    @property
    def _normal_attrs(self):
        """Provides a list of attribute names that should not be treated as
        extra data.

        Subclasses must implement if they use additional attributes they don't
        want shoved in extra_data.
        """
        return {'provider_uuid', 'provider_key', 'extra_data'}

    def __getattr__(self, name):
        try:
            return self.extra_data[name]
        except KeyError:
            raise AttributeError

    def __setattr__(self, name, value):
        if name in self._normal_attrs:
            super(_AbstractAuthenticated, self).__setattr__(name, value)
        else:
            if self.extra_data is None:
                self.extra_data = {}
            self.extra_data[name] = value

    def __delattr__(self, name):
        try:
            del self.extra_data[name]
        except KeyError:
            raise AttributeError

    def __hash__(self):
        return hash(self.provider_uuid) ^ hash(self.provider_key)

    def __eq__(self, other):
        return self.provider_uuid == other.provider_uuid and \
               self.provider_key == other.provider_key


class AuthenticatedUser(_AbstractAuthenticated):

    def __init__(self, **kwargs):
        self.user_id = util.id_from_kwargs('user', kwargs)
        kwargs.pop('user', None)
        kwargs.pop('user_id', None)
        super(AuthenticatedUser, self).__init__(**kwargs)

    @classmethod
    def from_dict(cls, user_dict):
        return cls(user_id=user_dict['user_id'],
                   provider_uuid=user_dict['provider_uuid'],
                   provider_key=user_dict['provider_key'],
                   extra_data=user_dict['extra_data'])

    @property
    def _normal_attrs(self):
        super_attrs = super(AuthenticatedUser, self)._normal_attrs
        return super_attrs.union({'user_id', })

class AuthenticatedGroup(_AbstractAuthenticated):

    def __init__(self, **kwargs):
        self.group_id = util.id_from_kwargs('group', kwargs)
        kwargs.pop('group', None)
        kwargs.pop('group_id', None)
        super(AuthenticatedGroup, self).__init__(**kwargs)

    @classmethod
    def from_dict(cls, group_dict):
        return cls(group_id=group_dict['group_id'],
                   provider_uuid=group_dict['provider_uuid'],
                   provider_key=group_dict['provider_key'],
                   extra_data=group_dict['extra_data'])

    @property
    def _normal_attrs(self):
        super_attrs = super(AuthenticatedGroup, self)._normal_attrs
        return super_attrs.union({'group_id', })

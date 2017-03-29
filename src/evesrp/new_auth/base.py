import collections
import enum
import uuid


class LoginFieldType(enum.Enum):

    string = 0
    """An unmasked string value, like for a username."""

    password = 1
    """A masked string value, like for a password."""


class AuthenticationProvider(object):

    __namespace_uuid = uuid.UUID('d6ffa87f-eea7-4318-81d1-7ee6a51433cc')

    def __init__(self, store, name=None):
        self.store = store
        self.name = name

    @property
    def name(self):
        """A name to be shown to a user identifying this provider."""
        if self._name is None:
            return u"Base Authentication"
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def fields(self):
        """A map of the fields needed to log in with this provider.

        The keys in the map are the keys for the fields that are passed in to
        `create_context`, as unicode strings. The values are members of
        :pt:class:`LoginFieldType` corresponding to the type of field.

        An additional key `u'submit'` is provided to customize the login text
        on the button. The value may be either a plain string, or it can be a
        tuple of alt text and either a URL or the name of an image to display.
        If not provided, the text on the button will be "Log In".

        :rtype: :py:class:`collections.OrderedDict`
        """
        fields = collections.OrderedDict()
        fields[u'submit'] = u'Log In'
        return fields


    @property
    def uuid(self):
        # If you're subclassing (either directly or indirectly) from
        # `AuthenticationProvider` and are reimplemeting `uuid`, you MUST
        # define your own `__namespace_uuid`.
        # This implementation is _intentionally_ nearly useless, serving only
        # as a way to distinguish unconfigurable subclasses from each other.
        return uuid.uuid5(self.__namespace_uuid, self.__class__.__name__)

    def create_context(self, **kwargs):
        """
        Return value is a dict. The main key is 'action', and details what was
        done.
        If 'action' is 'error', an error has occured. More details will
        be in the 'error' key.
        If 'action' is 'redirect', the view should direct the user to go to the
        URL given in the 'url' key. There may also be a 'state' key that the
        view should hold on to.
        If 'action' is 'success', the context to other AuthenticationProvider
        methods will be in the 'context' key. This value is opaque.
        """
        raise NotImplementedError

    def get_user(self, context, current_user=None):
        """Get a user identity for the given context.

        If this is a new identity an current_user is given, the identity is
        associated with that user. Otherwise, a new user is created.
        :param context: The context created by
            :py:method:`OAuth2Session.create_context`.
        :param current_user:
        :type current_user: :py:class:`~.User` or `None`
        :rtype: :py:class:`~.AuthenticatedUser`
        """
        raise NotImplementedError

    def get_characters(self, context):
        """Get a list of the characters associated with a context.

        Returns a :py:class:`list` of :py:class:`dict` objects, with the keys
        `id` and `name` for the character's ID number and name respectively.
        :param context: The context created by
            :py:method:`OAuth2Session.create_context`.
        :rtype: :py:class:`list`
        """
        raise NotImplementedError

    def get_groups(self, context):
        """Get a list of the group identities for the given context.

        :param context: The context created by
            :py:method:`OAuth2Session.create_context`.
            :rtype: :py:class:`list` of :py:class:`~.AuthenticatedGroup`
        """
        raise NotImplementedError


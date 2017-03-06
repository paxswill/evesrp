import uuid


class AuthenticationProvider(object):

    __namespace_uuid = uuid.UUID('d6ffa87f-eea7-4318-81d1-7ee6a51433cc')

    def __init__(self, store):
        self.store = store

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
        raise NotImplementedError

    def get_pilots(self, context):
        raise NotImplementedError

    def get_groups(self, context):
        raise NotImplementedError

